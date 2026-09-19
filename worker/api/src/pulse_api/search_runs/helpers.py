from __future__ import annotations

from fastapi import HTTPException, status

from ..post_search.sessions import PostSearchSession, PostSearchSessionManager
from ..job_search.sessions import JobSearchSession, JobSearchSessionManager
from .service import (
    InitiatedBy,
    attach_session_id,
    create_job_search_run,
    create_post_search_run,
)


def start_post_search_session(
    *,
    sessions: PostSearchSessionManager,
    user_id: str,
    post_search_id: str,
    limit: int,
    account_label: str | None,
    initiated_by: InitiatedBy = "user",
    admin_actor_id: str | None = None,
) -> PostSearchSession:
    try:
        run_id = create_post_search_run(
            user_id=user_id,
            post_search_id=post_search_id,
            limit=limit,
            account_label=account_label,
            initiated_by=initiated_by,
            admin_actor_id=admin_actor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create search run."
        ) from e

    sess = sessions.start(
        user_id=user_id,
        post_search_id=post_search_id,
        limit=limit,
        account_label=account_label,
        search_run_id=run_id,
    )
    attach_session_id(run_id=run_id, session_id=sess.session_id)
    return sess


def start_job_search_session(
    *,
    sessions: JobSearchSessionManager,
    user_id: str,
    job_search_id: str,
    limit: int,
    account_label: str | None,
    initiated_by: InitiatedBy = "user",
    admin_actor_id: str | None = None,
) -> JobSearchSession:
    try:
        run_id = create_job_search_run(
            user_id=user_id,
            job_search_id=job_search_id,
            limit=limit,
            account_label=account_label,
            initiated_by=initiated_by,
            admin_actor_id=admin_actor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create search run."
        ) from e

    sess = sessions.start(
        user_id=user_id,
        job_search_id=job_search_id,
        limit=limit,
        account_label=account_label,
        search_run_id=run_id,
    )
    attach_session_id(run_id=run_id, session_id=sess.session_id)
    return sess
