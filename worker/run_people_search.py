from __future__ import annotations

import argparse
import logging
import os
from dataclasses import replace
from datetime import UTC, datetime

from people_search import PeopleSearchService, PeopleSearchSpec  # type: ignore[import-not-found]
from people_search.adapters.linkedin_collector import LinkedInPeopleCollector  # type: ignore[import-not-found]
from people_search.adapters.llm_people_analyzer import LlmPeopleAnalyzer  # type: ignore[import-not-found]
from people_search.adapters.storage_repository import StoragePeopleRepository  # type: ignore[import-not-found]

from storage.facade import PulseStorage  # type: ignore[import-not-found]
from storage.domain.pulse import pick_linkedin_account_row  # type: ignore[import-not-found]
from post_analyzer.config import (  # type: ignore[import-not-found]
    LLMProviderSettings,
    load_llm_manager_settings_from_env,
)
from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

LLM_CONNECT_FAILED_EXIT_CODE = 2


def create_llm_manager() -> LLMProviderManager:
    mgr = LLMProviderManager(settings=load_llm_manager_settings_from_env())
    desc = mgr.describe()
    if desc.get("provider") != "fake" or desc.get("mode") != "fake":
        return mgr

    lmstudio_base_url = (
        os.getenv("POST_ANALYZER_OPENAI_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "http://127.0.0.1:1234/v1"
    )
    lmstudio_model = (
        os.getenv("POST_ANALYZER_LLM_MODEL")
        or os.getenv("POST_ANALYZER_OPENAI_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "deepseek-coder-v2-lite-instruct"
    )
    mgr.switch(
        primary=LLMProviderSettings(
            provider="openai",
            mode="real",
            model=lmstudio_model,
            base_url=lmstudio_base_url,
        ),
        fallback=None,
    )
    return mgr


def ensure_llm_connected() -> None:
    try:
        mgr = create_llm_manager()
        mgr.test_connection()
        desc = mgr.describe()
        log.info(
            "LLM connected: provider=%s model=%s",
            desc.get("provider") or "<unknown>",
            desc.get("model") or "<unknown>",
        )
    except SystemExit:
        raise
    except Exception as e:
        log.error("LLM not connected: %s", e)
        raise SystemExit(LLM_CONNECT_FAILED_EXIT_CODE) from None


def _required_env(name: str) -> str:
    if not (v := (os.getenv(name) or "").strip()):
        raise SystemExit(f"Missing required env var: {name}")
    return v


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run LinkedIn People Search pipeline.")
    p.add_argument("--people-search-id", required=True)
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--target-found", type=int, default=10)
    p.add_argument("--account-label", default=None)
    p.add_argument("--headless", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    ensure_llm_connected()

    user_id = _required_env("STORAGE_USER_ID")
    people_search_id = str(args.people_search_id)
    search_run_id = (os.getenv("SEARCH_RUN_ID") or "").strip() or None
    limit = int(args.limit or 25)
    min_score = int(args.min_score or 0)
    target_found = int(args.target_found or 10)
    account_label = str(args.account_label) if args.account_label else os.getenv("STORAGE_ACCOUNT_LABEL")

    storage = PulseStorage()
    row = storage.people_searches.get_by_id(people_search_id=people_search_id)
    if not row or row.get("user_id") != user_id:
        raise SystemExit("ERROR: people_search not found")
    if row.get("status") == "paused":
        log.info("People search is paused; skipping.")
        return

    title = str(row.get("title") or "People search")
    query = str(row.get("search_query") or "").strip()
    prompt = str(row.get("prompt") or "")
    filters = row.get("linkedin_filters") if isinstance(row.get("linkedin_filters"), dict) else None
    if not query:
        raise SystemExit("ERROR: search_query is empty")
    if not prompt:
        raise SystemExit("ERROR: people prompt is empty")

    accounts = storage.linkedin_accounts.list_by_user(user_id=user_id)
    account = pick_linkedin_account_row(
        accounts,
        label=account_label,
        create_new_on_label_miss=False,
    )
    if not account:
        raise SystemExit("ERROR: no LinkedIn account found (login required)")

    linkedin_account_id = str(account.get("id") or "")
    snapshot = account.get("session_snapshot") if isinstance(account.get("session_snapshot"), dict) else None
    if not snapshot:
        raise SystemExit("ERROR: LinkedIn session_snapshot is missing (re-login required)")

    from linkedin_client import LinkedInClient, LinkedInClientConfig  # type: ignore[import-not-found]

    cfg = LinkedInClientConfig()
    cfg = replace(cfg, browser=replace(cfg.browser, headless=bool(args.headless)))

    spec = PeopleSearchSpec(
        people_search_id=people_search_id,
        title=title,
        query=query,
        prompt=prompt,
        limit=limit,
        min_score=min_score,
        target_found=target_found,
        filters=filters,
    )

    mgr = create_llm_manager()
    mgr.test_connection()
    analyzer = LlmPeopleAnalyzer(llm_client=mgr)

    try:
        with LinkedInClient(config=cfg, session_snapshot=snapshot) as client:
            collector = LinkedInPeopleCollector(session=client)
            repo = StoragePeopleRepository(
                storage=storage,
                user_id=user_id,
                linkedin_account_id=linkedin_account_id,
            )
            svc = PeopleSearchService(collector=collector, analyzer=analyzer, repository=repo)
            r = svc.run(spec=spec)

        now = datetime.now(UTC).isoformat()
        storage.people_searches.update(people_search_id=people_search_id, last_run_at=now)

        if search_run_id:
            storage.search_runs.finalize(
                run_id=search_run_id,
                status="done",
                fetched_count=int(r.collected),
                analyzed_count=int(r.analyzed),
                matched_count=int(r.matched),
            )

        log.info(
            "People search done: collected=%s unique=%s analyzed=%s matched=%s enriched=%s errors=%s",
            r.collected,
            r.unique,
            r.analyzed,
            r.matched,
            r.enriched,
            r.errors,
        )
    except SystemExit:
        raise
    except Exception as e:
        if search_run_id:
            try:
                storage.search_runs.finalize(run_id=search_run_id, status="error", error=str(e))
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
