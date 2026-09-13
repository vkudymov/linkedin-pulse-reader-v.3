from __future__ import annotations

import argparse
import logging
import os
from dataclasses import replace
from datetime import UTC, datetime

from job_search import JobSearchService, JobSearchSpec  # type: ignore[import-not-found]
from job_search.adapters.linkedin_collector import LinkedInJobCollector  # type: ignore[import-not-found]
from job_search.adapters.llm_job_analyzer import LlmJobAnalyzer  # type: ignore[import-not-found]
from job_search.adapters.storage_repository import StorageJobRepository  # type: ignore[import-not-found]

from storage.facade import PulseStorage  # type: ignore[import-not-found]
from storage.domain.pulse import pick_linkedin_account_row  # type: ignore[import-not-found]


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

LLM_CONNECT_FAILED_EXIT_CODE = 2


def ensure_llm_connected() -> None:
    try:
        from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]
        from post_analyzer.config import load_llm_manager_settings_from_env  # type: ignore[import-not-found]

        settings = load_llm_manager_settings_from_env()
        mgr = LLMProviderManager(settings=settings)
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
    v = (os.getenv(name) or "").strip()
    if not v:
        raise SystemExit(f"Missing required env var: {name}")
    return v


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run LinkedIn Job Search pipeline.")
    p.add_argument("--job-search-id", required=True)
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--account-label", default=None)
    p.add_argument("--headless", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    ensure_llm_connected()

    user_id = _required_env("STORAGE_USER_ID")
    job_search_id = str(args.job_search_id)
    limit = int(args.limit or 25)
    account_label = str(args.account_label) if args.account_label else os.getenv("STORAGE_ACCOUNT_LABEL")

    storage = PulseStorage()

    js_row = storage.job_searches.get_by_id(job_search_id=job_search_id)
    if not js_row or js_row.get("user_id") != user_id:
        raise SystemExit("ERROR: job_search not found")
    if js_row.get("status") == "paused":
        log.info("Job search is paused; skipping.")
        return

    title = str(js_row.get("title") or "Job search")
    search_query = str(js_row.get("search_query") or "").strip()
    location = js_row.get("location") if isinstance(js_row.get("location"), str) else None
    filter_prompt = str(js_row.get("filter_prompt") or "")

    if not search_query:
        raise SystemExit("ERROR: search_query is empty")
    if not filter_prompt:
        raise SystemExit("ERROR: filter_prompt is empty")

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

    spec = JobSearchSpec(
        job_search_id=job_search_id,
        title=title,
        search_query=search_query,
        location=location,
        filter_prompt=filter_prompt,
        limit=limit,
    )

    from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]
    from post_analyzer.config import load_llm_manager_settings_from_env  # type: ignore[import-not-found]

    mgr = LLMProviderManager(settings=load_llm_manager_settings_from_env())
    analyzer = LlmJobAnalyzer(llm_client=mgr)

    with LinkedInClient(config=cfg, session_snapshot=snapshot) as client:
        collector = LinkedInJobCollector(client=client)
        repo = StorageJobRepository(
            storage=storage,
            user_id=user_id,
            linkedin_account_id=linkedin_account_id,
        )
        svc = JobSearchService(collector=collector, analyzer=analyzer, repository=repo)
        r = svc.run(spec=spec)

    now = datetime.now(UTC).isoformat()
    storage.job_searches.update(job_search_id=job_search_id, last_run_at=now)

    log.info(
        "Job search done: collected=%s unique=%s analyzed=%s matched=%s errors=%s",
        r.collected,
        r.unique,
        r.analyzed,
        r.matched,
        r.errors,
    )


if __name__ == "__main__":
    main()

