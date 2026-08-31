from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import require_user_id
from ..post_search.routes import _ensure_not_blocked_and_increment_counter  # type: ignore
from ..post_search.schemas import PostSearchRunResponse, PostSearchStartRequest
from ..post_search.sessions import PostSearchSessionManager
from ..settings import get_settings
from .schemas import (
    AdminUserProfileDetails,
    AdminUserProfileUpdate,
    AdminUserPromptsDetails,
    AdminUserPromptsUpdate,
    AdminUserRow,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])
_admin_sessions = PostSearchSessionManager()


def _get_service_client() -> Any:
    settings = get_settings()
    from supabase import create_client  # type: ignore[import-untyped]

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def require_admin_user_id(user_id: str = Depends(require_user_id)) -> str:
    client = _get_service_client()
    try:
        resp = (
            client.table("user_admin_state")
            .select("is_admin")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin check failed.") from e

    row = getattr(resp, "data", None)
    is_admin = False
    if isinstance(row, dict):
        is_admin = bool(row.get("is_admin"))
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")
    return user_id


@router.get("/users", response_model=list[AdminUserRow])
def list_users(_: str = Depends(require_admin_user_id)) -> list[AdminUserRow]:
    client = _get_service_client()

    # Human profiles (DB)
    try:
        prof_resp = client.table("user_profiles").select("id,full_name,created_at").execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load profiles.") from e

    profiles_raw = getattr(prof_resp, "data", None)
    profiles: list[dict[str, Any]] = (
        [p for p in profiles_raw if isinstance(p, dict)] if isinstance(profiles_raw, list) else []
    )
    profile_by_id: dict[str, dict[str, Any]] = {p.get("id"): p for p in profiles if p.get("id")}

    # Admin state (DB)
    try:
        st_resp = client.table("user_admin_state").select(
            "id,is_admin,is_blocked,blocked_at,post_search_run_count"
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load admin state.") from e

    st_raw = getattr(st_resp, "data", None)
    states: list[dict[str, Any]] = (
        [s for s in st_raw if isinstance(s, dict)] if isinstance(st_raw, list) else []
    )
    state_by_id: dict[str, dict[str, Any]] = {s.get("id"): s for s in states if s.get("id")}

    # Auth users (email)
    emails_by_id: dict[str, str] = {}
    try:
        page = 1
        per_page = 1000
        while True:
            auth_resp = client.auth.admin.list_users(page=page, per_page=per_page)  # type: ignore[attr-defined]
            users = getattr(auth_resp, "users", None)
            if users is None and isinstance(auth_resp, dict):
                users = auth_resp.get("users")
            if not isinstance(users, list) or len(users) == 0:
                break
            for u in users:
                if isinstance(u, dict):
                    uid = u.get("id")
                    email = u.get("email")
                else:
                    uid = getattr(u, "id", None)
                    email = getattr(u, "email", None)
                if isinstance(uid, str) and uid and isinstance(email, str) and email:
                    emails_by_id[uid] = email
            if len(users) < per_page:
                break
            page += 1
    except Exception:
        # Fallback to per-user fetch below.
        emails_by_id = {}

    # Fallback: fetch email per user if list_users was unavailable.
    if not emails_by_id:
        for uid in profile_by_id.keys():
            try:
                u = client.auth.admin.get_user_by_id(uid)  # type: ignore[attr-defined]
                user_obj = getattr(u, "user", None)
                if user_obj is None and isinstance(u, dict):
                    user_obj = u.get("user")
                email = None
                if isinstance(user_obj, dict):
                    email = user_obj.get("email")
                else:
                    email = getattr(user_obj, "email", None)
                if isinstance(email, str) and email:
                    emails_by_id[uid] = email
            except Exception:
                continue

    out: list[AdminUserRow] = []
    for uid, p in profile_by_id.items():
        st = state_by_id.get(uid, {})
        out.append(
            AdminUserRow(
                id=uid,
                email=emails_by_id.get(uid),
                created_at=p.get("created_at"),
                full_name=p.get("full_name"),
                is_admin=bool(st.get("is_admin")),
                is_blocked=bool(st.get("is_blocked")),
                blocked_at=st.get("blocked_at"),
                post_search_run_count=int(st.get("post_search_run_count") or 0),
            )
        )
    out.sort(key=lambda r: (r.created_at is None, r.created_at))
    return out


@router.get("/users/{target_user_id}/profile", response_model=AdminUserProfileDetails)
def get_user_profile_details(
    target_user_id: str, _: str = Depends(require_admin_user_id)
) -> AdminUserProfileDetails:
    client = _get_service_client()
    try:
        resp = (
            client.table("user_profiles")
            .select(
                "id,full_name,phone,avatar_url,company,job_title,date_of_birth,city,bio,website,created_at,updated_at"
            )
            .eq("id", target_user_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load profile.") from e
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return AdminUserProfileDetails(**row)


def _to_nullable_trimmed_string(v: str | None) -> str | None:
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


def _to_nullable_date(v: str | None) -> str | None:
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    try:
        # Keep as ISO string for PostgREST JSON payload.
        date.fromisoformat(s)
        return s  # type: ignore[return-value]
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_of_birth.")


@router.post("/users/{target_user_id}/profile")
def update_user_profile_details(
    target_user_id: str,
    body: AdminUserProfileUpdate,
    _: str = Depends(require_admin_user_id),
) -> dict[str, Any]:
    client = _get_service_client()
    payload: dict[str, Any] = {
        "id": target_user_id,
        "full_name": _to_nullable_trimmed_string(body.full_name),
        "phone": _to_nullable_trimmed_string(body.phone),
        "avatar_url": _to_nullable_trimmed_string(body.avatar_url),
        "company": _to_nullable_trimmed_string(body.company),
        "job_title": _to_nullable_trimmed_string(body.job_title),
        "date_of_birth": _to_nullable_date(body.date_of_birth),
        "city": _to_nullable_trimmed_string(body.city),
        "bio": _to_nullable_trimmed_string(body.bio),
        "website": _to_nullable_trimmed_string(body.website),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = client.table("user_profiles").upsert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile.") from e
    err = getattr(resp, "error", None)
    if err:
        msg = getattr(err, "message", None) if err is not None else None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(msg if isinstance(msg, str) and msg else "Failed to update profile."),
        )
    return {"ok": True}


_SEARCH_REQUIRED_MARKER = "<<<POST_TEXT>>>"
_COMMENT_REQUIRED_MARKERS = [
    "<<<POST_TEXT>>>",
    "<<<CONTENT_TYPE>>>",
    "<<<MAIN_TOPICS>>>",
    "<<<TARGET_LANGUAGE>>>",
]


def _missing_markers(value: str, markers: list[str]) -> list[str]:
    v = value or ""
    return [m for m in markers if m not in v]


def _validate_prompts(*, search_prompt: str | None, comment_prompt: str | None) -> tuple[str, str | None]:
    s = _to_nullable_trimmed_string(search_prompt)
    c = _to_nullable_trimmed_string(comment_prompt)
    if not s:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Промпт поиска обязателен.")
    if _SEARCH_REQUIRED_MARKER not in s:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Промпт поиска должен содержать маркер {_SEARCH_REQUIRED_MARKER}.",
        )
    if c:
        missing = _missing_markers(c, _COMMENT_REQUIRED_MARKERS)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Промпт комментария должен содержать маркеры: {', '.join(missing)}.",
            )
    return s, c


@router.get("/users/{target_user_id}/prompts", response_model=AdminUserPromptsDetails)
def get_user_prompts_details(
    target_user_id: str, _: str = Depends(require_admin_user_id)
) -> AdminUserPromptsDetails:
    client = _get_service_client()
    try:
        resp = (
            client.table("user_prompts")
            .select("id,search_prompt,comment_prompt,created_at,updated_at")
            .eq("id", target_user_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load prompts.") from e
    row = getattr(resp, "data", None)
    # Row may not exist yet for legacy users; return empty record shape.
    if not isinstance(row, dict) or not row.get("id"):
        return AdminUserPromptsDetails(id=target_user_id)
    return AdminUserPromptsDetails(**row)


@router.post("/users/{target_user_id}/prompts")
def update_user_prompts_details(
    target_user_id: str,
    body: AdminUserPromptsUpdate,
    _: str = Depends(require_admin_user_id),
) -> dict[str, Any]:
    client = _get_service_client()
    search_prompt, comment_prompt = _validate_prompts(
        search_prompt=body.search_prompt, comment_prompt=body.comment_prompt
    )
    payload: dict[str, Any] = {
        "id": target_user_id,
        "search_prompt": search_prompt,
        "comment_prompt": comment_prompt,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = client.table("user_prompts").upsert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update prompts.") from e
    err = getattr(resp, "error", None)
    if err:
        msg = getattr(err, "message", None) if err is not None else None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(msg if isinstance(msg, str) and msg else "Failed to update prompts."),
        )
    return {"ok": True}


@router.post("/users/{target_user_id}/post-search/run", response_model=PostSearchRunResponse)
def admin_start_post_search_run(
    target_user_id: str,
    req: PostSearchStartRequest,
    _: str = Depends(require_admin_user_id),
) -> PostSearchRunResponse:
    _ensure_not_blocked_and_increment_counter(user_id=target_user_id)
    sess = _admin_sessions.start(user_id=target_user_id, limit=req.limit, account_label=req.account_label)
    return PostSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


@router.get("/users/{target_user_id}/post-search/run/{session_id}", response_model=PostSearchRunResponse)
def admin_get_post_search_status(
    target_user_id: str,
    session_id: str,
    _: str = Depends(require_admin_user_id),
) -> PostSearchRunResponse:
    sess = _admin_sessions.get(user_id=target_user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return PostSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


def _set_blocked(*, user_id: str, blocked: bool) -> None:
    client = _get_service_client()
    payload: dict[str, Any] = {
        "id": user_id,
        "is_blocked": blocked,
        "blocked_at": (datetime.now(timezone.utc).isoformat() if blocked else None),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.table("user_admin_state").upsert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed.") from e


@router.post("/users/{target_user_id}/block")
def block_user(target_user_id: str, _: str = Depends(require_admin_user_id)) -> dict[str, Any]:
    _set_blocked(user_id=target_user_id, blocked=True)
    return {"ok": True}


@router.post("/users/{target_user_id}/unblock")
def unblock_user(target_user_id: str, _: str = Depends(require_admin_user_id)) -> dict[str, Any]:
    _set_blocked(user_id=target_user_id, blocked=False)
    return {"ok": True}


@router.post("/users/{target_user_id}/reset-post-search-count")
def reset_post_search_count(target_user_id: str, _: str = Depends(require_admin_user_id)) -> dict[str, Any]:
    client = _get_service_client()
    payload: dict[str, Any] = {
        "id": target_user_id,
        "post_search_run_count": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.table("user_admin_state").upsert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Reset failed.") from e
    return {"ok": True}

