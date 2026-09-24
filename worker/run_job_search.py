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

    # Auto-switch to a local OpenAI-compatible server (LM Studio) if LLM is left in fake mode.
    # Mirrors behavior in run_post_search.py to avoid confusing score=0 everywhere.
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
    p = argparse.ArgumentParser(description="Run LinkedIn Job Search pipeline.")
    p.add_argument("--job-search-id", required=True)
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
    job_search_id = str(args.job_search_id)
    search_run_id = (os.getenv("SEARCH_RUN_ID") or "").strip() or None
    limit = int(args.limit or 25)
    min_score = int(args.min_score or 0)
    target_found = int(args.target_found or 10)
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
    linkedin_filters = js_row.get("linkedin_filters") if isinstance(js_row.get("linkedin_filters"), dict) else None

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
        min_score=min_score,
        target_found=target_found,
        linkedin_filters=linkedin_filters,
    )

    mgr = create_llm_manager()
    # Fail fast if LM Studio isn't reachable (or provider is misconfigured).
    mgr.test_connection()
    analyzer = LlmJobAnalyzer(llm_client=mgr)

    try:
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

        if search_run_id:
            storage.search_runs.finalize(
                run_id=search_run_id,
                status="done",
                fetched_count=int(r.collected),
                analyzed_count=int(r.analyzed),
                matched_count=int(r.matched),
            )

        _maybe_send_email_report(
            storage=storage,
            user_id=user_id,
            job_search_row=js_row,
            run_at=now,
            fetched_count=int(r.collected),
            analyzed_count=int(r.analyzed),
            matched_count=int(r.matched),
            report_items=list(getattr(r, "report_items", ()) or ()),
            min_score=min_score,
            target_found=target_found,
        )

        log.info(
            "Job search done: collected=%s unique=%s analyzed=%s matched=%s errors=%s",
            r.collected,
            r.unique,
            r.analyzed,
            r.matched,
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


def _maybe_send_email_report(
    *,
    storage: PulseStorage,
    user_id: str,
    job_search_row: dict[str, Any],
    run_at: str,
    fetched_count: int,
    analyzed_count: int,
    matched_count: int,
    report_items: list[dict[str, object]],
    min_score: int,
    target_found: int,
) -> None:
    """
    Best-effort: send a report email (never fails the run).
    """
    try:
        from search_report_mailer.types import ReportItem, ReportMeta
        from search_report_integration.dispatch import dispatch_report, default_body, default_subject
        from search_report_integration.policy import should_send_email_report
        from search_report_integration.user_email import get_user_email
    except Exception:
        return

    try:
        tariff_row = storage.search_tariffs.resolve(tariff_id=job_search_row.get("search_tariff_id"))
        should_send, fmt = should_send_email_report(tariff_row=tariff_row, search_row=job_search_row)
        if not should_send:
            return

        email = get_user_email(client=storage.client, user_id=user_id)
        if not email:
            log.warning("Email report is enabled, but user email is missing (user_id=%s)", user_id)
            return

        items: list[ReportItem] = []
        for d in report_items:
            job = d.get("job") if isinstance(d.get("job"), dict) else {}
            items.append(
                ReportItem(
                    kind="job",
                    analyzed=bool(d.get("analyzed")),
                    match=d.get("match") if isinstance(d.get("match"), bool) else None,
                    score=int(d.get("score")) if isinstance(d.get("score"), int) else None,
                    reason=d.get("reason") if isinstance(d.get("reason"), str) else None,
                    matched_requirements=tuple(
                        x for x in (d.get("matched_requirements") or []) if isinstance(x, str)
                    ),
                    missing_requirements=tuple(
                        x for x in (d.get("missing_requirements") or []) if isinstance(x, str)
                    ),
                    red_flags=tuple(x for x in (d.get("red_flags") or []) if isinstance(x, str)),
                    title=job.get("title") if isinstance(job.get("title"), str) else None,
                    url=job.get("job_url") if isinstance(job.get("job_url"), str) else None,
                    company=job.get("company") if isinstance(job.get("company"), str) else None,
                    location=job.get("location") if isinstance(job.get("location"), str) else None,
                    description=job.get("description") if isinstance(job.get("description"), str) else None,
                    extra=None,
                )
            )

        search_title = str(job_search_row.get("title") or "Job search")
        meta = ReportMeta(
            kind="job",
            search_title=search_title,
            run_at_iso=run_at,
            min_score=int(min_score or 0),
            target_found=int(target_found or 0),
            fetched_count=int(fetched_count),
            analyzed_count=int(analyzed_count),
            matched_count=int(matched_count),
        )
        subject = default_subject(kind="jobs", search_title=search_title)
        body = default_body(kind="jobs", search_title=search_title) + f"\n\nFetched: {fetched_count}\nAnalyzed: {analyzed_count}\nMatched: {matched_count}\n"

        r = dispatch_report(
            to_email=email,
            subject=subject,
            body_text=body,
            file_format=fmt,
            items=items,
            meta=meta,
        )
        if not r.ok:
            log.warning("Failed to send email report: %s", r.error or "<unknown>")
    except Exception as e:
        log.warning("Email report failed (ignored): %s", e)


if __name__ == "__main__":
    main()

