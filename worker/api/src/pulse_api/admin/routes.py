from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import require_user_id
from ..job_search.schemas import JobSearchRunResponse, JobSearchStartRequest
from ..job_search.sessions import JobSearchSessionManager
from ..post_search.routes import _ensure_not_blocked_and_increment_counter  # type: ignore
from ..post_search.schemas import PostSearchRunResponse
from ..post_search.sessions import PostSearchSessionManager
from ..search_runs.helpers import start_job_search_session, start_post_search_session
from ..settings import get_settings
from .schemas import (
    AdminJobSearchRow,
    AdminJobSearchUpdate,
    AdminPostSearchRow,
    AdminPostSearchStartRequest,
    AdminPostSearchUpdate,
    AdminPromptRow,
    AdminPromptUpdate,
    AdminSearchTariffCreate,
    AdminSearchTariffRow,
    AdminSearchTariffUpdate,
    AdminSearchRow,
    AdminSearchUpdate,
    AdminSearchesListResponse,
    AdminSearchRunRow,
    AdminSearchRunsListResponse,
    AdminPromptsListResponse,
    AdminUserProfileDetails,
    AdminUserProfileUpdate,
    AdminUserPromptsDetails,
    AdminUserPromptsUpdate,
    AdminUserSearchTariffUpdate,
    AdminUserRow,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])
_admin_sessions = PostSearchSessionManager()
_admin_job_sessions = JobSearchSessionManager()


def _get_service_client() -> Any:
    settings = get_settings()
    from supabase import create_client  # type: ignore[import-untyped]

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


_SEARCH_TYPE_ID_CACHE: dict[str, str] = {}


def _search_type_id(*, client: Any, code: str) -> str:
    cached = _SEARCH_TYPE_ID_CACHE.get(code)
    if cached:
        return cached
    resp = client.table("search_types").select("id").eq("code", code).maybe_single().execute()
    row = getattr(resp, "data", None)
    tid = str(row.get("id") or "") if isinstance(row, dict) else ""
    if not tid:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Missing search_types: {code}")
    _SEARCH_TYPE_ID_CACHE[code] = tid
    return tid


def _job_row_from_search(*, search_row: dict[str, Any]) -> dict[str, Any]:
    prompts = search_row.get("prompts")
    filter_prompt = ""
    if isinstance(prompts, list):
        for p in prompts:
            if isinstance(p, dict) and p.get("role") == "filter" and isinstance(p.get("body"), str):
                filter_prompt = str(p.get("body") or "")
                break
    out = dict(search_row)
    out.pop("prompts", None)
    out.pop("search_type_id", None)
    out["filter_prompt"] = filter_prompt
    return out


def _post_prompts_from_search(*, search_row: dict[str, Any]) -> tuple[str, str | None]:
    prompts = search_row.get("prompts")
    search_prompt = ""
    comment_prompt: str | None = None
    if isinstance(prompts, list):
        for p in prompts:
            if not isinstance(p, dict) or not isinstance(p.get("body"), str):
                continue
            if p.get("role") == "search":
                search_prompt = str(p.get("body") or "")
            elif p.get("role") == "comment":
                comment_prompt = str(p.get("body") or "")
    return search_prompt, comment_prompt


def _admin_search_row_from_search(*, search_row: dict[str, Any]) -> dict[str, Any]:
    st = search_row.get("search_types")
    code = st.get("code") if isinstance(st, dict) else None
    search_type_code = str(code or "")
    prompts = search_row.get("prompts")
    prompts_list: list[dict[str, Any]] = [p for p in prompts if isinstance(p, dict)] if isinstance(prompts, list) else []

    filter_prompt = None
    search_prompt = None
    comment_prompt = None
    if search_type_code == "jobs":
        for p in prompts_list:
            if p.get("role") == "filter" and isinstance(p.get("body"), str):
                filter_prompt = str(p.get("body") or "")
                break
    elif search_type_code == "posts":
        sp, cp = _post_prompts_from_search(search_row=search_row)
        search_prompt = sp
        comment_prompt = cp

    out = dict(search_row)
    out.pop("search_type_id", None)
    out["search_type_code"] = search_type_code
    out["prompts"] = prompts_list
    out["filter_prompt"] = filter_prompt
    out["search_prompt"] = search_prompt
    out["comment_prompt"] = comment_prompt
    return out

def _ensure_not_blocked(*, user_id: str) -> None:
    client = _get_service_client()
    try:
        resp = (
            client.table("user_admin_state")
            .select("is_blocked")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Profile check failed.") from e
    row = getattr(resp, "data", None)
    is_blocked = bool(row.get("is_blocked")) if isinstance(row, dict) else False
    if is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь заблокирован.")


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
    is_admin = bool(row.get("is_admin")) if isinstance(row, dict) else False
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
        for uid in profile_by_id:
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
    try:
        st_resp = (
            client.table("user_admin_state")
            .select("search_tariff_id")
            .eq("id", target_user_id)
            .maybe_single()
            .execute()
        )
        st_row = getattr(st_resp, "data", None)
        if isinstance(st_row, dict):
            row["search_tariff_id"] = st_row.get("search_tariff_id")
    except Exception:
        # Non-critical for profile details.
        row["search_tariff_id"] = None
    return AdminUserProfileDetails(**row)


def _to_nullable_trimmed_string(v: str | None) -> str | None:
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


def _first_updated_row(resp: Any) -> dict[str, Any] | None:
    data = getattr(resp, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def _load_user_names(*, client: Any, user_ids: list[str]) -> dict[str, str | None]:
    if not user_ids:
        return {}
    try:
        prof = client.table("user_profiles").select("id,full_name").in_("id", user_ids).execute()
        data = getattr(prof, "data", None)
        if not isinstance(data, list):
            return {}
        out: dict[str, str | None] = {}
        for p in data:
            if isinstance(p, dict) and p.get("id"):
                out[str(p["id"])] = p.get("full_name") if isinstance(p.get("full_name"), str) else None
        return out
    except Exception:
        return {}


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
    if err := getattr(resp, "error", None):
        msg = getattr(err, "message", None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(msg if isinstance(msg, str) and msg else "Failed to update profile."),
        )
    return {"ok": True}


@router.get("/search-tariffs", response_model=list[AdminSearchTariffRow])
def list_search_tariffs(_: str = Depends(require_admin_user_id)) -> list[AdminSearchTariffRow]:
    client = _get_service_client()
    try:
        resp = (
            client.table("search_tariffs")
            .select("*")
            .order("sort_order", desc=False)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load search tariffs.") from e
    data = getattr(resp, "data", None)
    rows = [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
    return [AdminSearchTariffRow(**r) for r in rows]


@router.post("/search-tariffs", response_model=AdminSearchTariffRow)
def create_search_tariff(
    body: AdminSearchTariffCreate, _: str = Depends(require_admin_user_id)
) -> AdminSearchTariffRow:
    client = _get_service_client()
    payload = body.model_dump()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        resp = client.table("search_tariffs").insert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create search tariff.") from e
    row = getattr(resp, "data", None)
    if isinstance(row, list) and row and isinstance(row[0], dict):
        return AdminSearchTariffRow(**row[0])
    if isinstance(row, dict):
        return AdminSearchTariffRow(**row)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid create response.")


@router.patch("/search-tariffs/{tariff_id}", response_model=AdminSearchTariffRow)
def update_search_tariff(
    tariff_id: str, body: AdminSearchTariffUpdate, _: str = Depends(require_admin_user_id)
) -> AdminSearchTariffRow:
    client = _get_service_client()
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        resp = client.table("search_tariffs").update(patch).eq("id", tariff_id).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update search tariff.") from e
    data = getattr(resp, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return AdminSearchTariffRow(**data[0])
    if isinstance(data, dict):
        return AdminSearchTariffRow(**data)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found.")


@router.delete("/search-tariffs/{tariff_id}")
def delete_search_tariff(tariff_id: str, _: str = Depends(require_admin_user_id)) -> dict[str, Any]:
    client = _get_service_client()
    try:
        count_resp = client.table("search_tariffs").select("id", count="exact").execute()
        total = getattr(count_resp, "count", None)
        if isinstance(total, int) and total <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить последний тариф.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check tariffs.") from e
    try:
        client.table("search_tariffs").delete().eq("id", tariff_id).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete search tariff.") from e
    return {"ok": True}


@router.post("/users/{target_user_id}/search-tariff")
def update_user_search_tariff(
    target_user_id: str,
    body: AdminUserSearchTariffUpdate,
    _: str = Depends(require_admin_user_id),
) -> dict[str, Any]:
    client = _get_service_client()
    payload = {
        "id": target_user_id,
        "search_tariff_id": body.search_tariff_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.table("user_admin_state").upsert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user tariff.") from e
    return {"ok": True}


_SEARCH_REQUIRED_MARKER = "<<<POST_TEXT>>>"
_COMMENT_REQUIRED_MARKERS = [
    "<<<POST_TEXT>>>",
    "<<<CONTENT_TYPE>>>",
    "<<<MAIN_TOPICS>>>",
    "<<<TARGET_LANGUAGE>>>",
]

_JOB_SEARCH_REQUIRED_MARKER = "<<<JOB_TEXT>>>"


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
    if c and (missing := _missing_markers(c, _COMMENT_REQUIRED_MARKERS)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Промпт комментария должен содержать маркеры: {', '.join(missing)}.",
        )
    return s, c


def _require_non_empty_string(v: str | None, *, field: str) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}.")
    if not (s := v.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} must be non-empty.")
    return s


def _validate_job_search_filter_prompt(v: str | None) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filter_prompt.")
    if not (s := v.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filter_prompt must be non-empty.")
    if _JOB_SEARCH_REQUIRED_MARKER not in s:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"filter_prompt must contain marker {_JOB_SEARCH_REQUIRED_MARKER}.",
        )
    return s


_EMAIL_REPORT_FORMATS = {"none", "xlsx", "docx", "txt", "json", "xml"}


def _validate_email_report_format(v: str | None) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email_report_format.")
    s = v.strip().lower()
    if s not in _EMAIL_REPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email_report_format. Allowed: {', '.join(sorted(_EMAIL_REPORT_FORMATS))}.",
        )
    return s


def _resolve_tariff_email_reports_enabled(*, client: Any, tariff_id: str | None) -> bool:
    """
    Best-effort: read search_tariffs.email_reports_enabled.
    Falls back to default tariff if tariff_id is missing/invalid.
    If the column isn't present yet, returns False.
    """
    try:
        row: dict[str, Any] | None = None
        if tariff_id:
            resp = (
                client.table("search_tariffs")
                .select("email_reports_enabled")
                .eq("id", tariff_id)
                .maybe_single()
                .execute()
            )
            data = getattr(resp, "data", None)
            row = data if isinstance(data, dict) else None
        if not row:
            resp = (
                client.table("search_tariffs")
                .select("email_reports_enabled")
                .order("sort_order", desc=False)
                .order("created_at", desc=False)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", None)
            if isinstance(data, list) and data and isinstance(data[0], dict):
                row = data[0]
            elif isinstance(data, dict):
                row = data
        return bool(row and row.get("email_reports_enabled") is True)
    except Exception:
        return False


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
    # Row may not exist yet for legacy users; return empty record shape.
    if not isinstance((row := getattr(resp, "data", None)), dict) or not row.get("id"):
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
    if err := getattr(resp, "error", None):
        msg = getattr(err, "message", None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(msg if isinstance(msg, str) and msg else "Failed to update prompts."),
        )
    return {"ok": True}


@router.get("/users/{target_user_id}/job-searches", response_model=list[AdminJobSearchRow])
def list_user_job_searches(
    target_user_id: str, _: str = Depends(require_admin_user_id)
) -> list[AdminJobSearchRow]:
    client = _get_service_client()
    try:
        resp = (
            client.table("searches")
            .select(
                "id,user_id,title,search_query,location,linkedin_filters,search_tariff_id,email_report_enabled,email_report_format,status,last_run_at,created_at,updated_at,search_type_id,prompts(role,body)"
            )
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="jobs"))
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load job searches."
        ) from e
    rows_raw = getattr(resp, "data", None)
    rows: list[dict[str, Any]] = (
        [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []
    )
    mapped = [_job_row_from_search(search_row=r) for r in rows if r.get("id")]
    return [AdminJobSearchRow(**r) for r in mapped if r.get("id")]


@router.patch("/users/{target_user_id}/job-searches/{job_search_id}", response_model=AdminJobSearchRow)
def update_user_job_search(
    target_user_id: str,
    job_search_id: str,
    body: AdminJobSearchUpdate,
    _: str = Depends(require_admin_user_id),
) -> AdminJobSearchRow:
    client = _get_service_client()
    payload: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

    title = _require_non_empty_string(body.title, field="title")
    search_query = _require_non_empty_string(body.search_query, field="search_query")
    location = _to_nullable_trimmed_string(body.location)
    filter_prompt = _validate_job_search_filter_prompt(body.filter_prompt)
    status_value = _to_nullable_trimmed_string(body.status)
    tariff_id = _to_nullable_trimmed_string(body.search_tariff_id)
    email_report_format = _validate_email_report_format(body.email_report_format)

    if title is not None:
        payload["title"] = title
    if search_query is not None:
        payload["search_query"] = search_query
    if body.location is not None:
        payload["location"] = location
    if filter_prompt is not None:
        # stored in prompts table
        pass
    if body.status is not None:
        payload["status"] = status_value
    if "search_tariff_id" in body.model_fields_set:
        payload["search_tariff_id"] = tariff_id
    if "email_report_enabled" in body.model_fields_set:
        payload["email_report_enabled"] = bool(body.email_report_enabled)
    if "email_report_format" in body.model_fields_set:
        payload["email_report_format"] = email_report_format or "none"

    # Enforce tariff capability for email reports.
    wants_email = bool(payload.get("email_report_enabled") is True)
    wants_format = bool(
        ("email_report_format" in payload)
        and isinstance(payload.get("email_report_format"), str)
        and payload.get("email_report_format") != "none"
    )
    if wants_email or wants_format:
        effective_tariff_id: str | None = None
        if "search_tariff_id" in payload:
            effective_tariff_id = payload.get("search_tariff_id") if isinstance(payload.get("search_tariff_id"), str) else None
        else:
            try:
                st = (
                    client.table("searches")
                    .select("search_tariff_id")
                    .eq("id", job_search_id)
                    .eq("user_id", target_user_id)
                    .eq("search_type_id", _search_type_id(client=client, code="jobs"))
                    .maybe_single()
                    .execute()
                )
                row = getattr(st, "data", None)
                effective_tariff_id = row.get("search_tariff_id") if isinstance(row, dict) else None
            except Exception:
                effective_tariff_id = None

        if not _resolve_tariff_email_reports_enabled(client=client, tariff_id=effective_tariff_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tariff does not allow email reports.",
            )

    # No-op update is allowed but should still validate ownership.
    try:
        prompt_to_save = filter_prompt
        if prompt_to_save is not None:
            # Remove prompt from search update payload.
            pass
        resp = (
            client.table("searches")
            .update(payload)
            .eq("id", job_search_id)
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="jobs"))
            .select(
                "id,user_id,title,search_query,location,linkedin_filters,search_tariff_id,email_report_enabled,email_report_format,status,last_run_at,created_at,updated_at,search_type_id,prompts(role,body)"
            )
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update job search."
        ) from e

    row = _first_updated_row(resp)
    if not row or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job search not found.")
    if prompt_to_save is not None:
        try:
            client.table("prompts").upsert(
                [{"search_id": job_search_id, "role": "filter", "body": prompt_to_save}],
                on_conflict="search_id,role",
            ).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update job prompt."
            ) from e
        # Re-fetch with prompts to return consistent row
        resp2 = (
            client.table("searches")
            .select(
                "id,user_id,title,search_query,location,linkedin_filters,search_tariff_id,email_report_enabled,email_report_format,status,last_run_at,created_at,updated_at,search_type_id,prompts(role,body)"
            )
            .eq("id", job_search_id)
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="jobs"))
            .maybe_single()
            .execute()
        )
        row2 = getattr(resp2, "data", None)
        if isinstance(row2, dict) and row2.get("id"):
            row = row2

    return AdminJobSearchRow(**_job_row_from_search(search_row=row))


@router.delete("/users/{target_user_id}/job-searches/{job_search_id}")
def delete_user_job_search(
    target_user_id: str,
    job_search_id: str,
    _: str = Depends(require_admin_user_id),
) -> dict[str, Any]:
    client = _get_service_client()
    try:
        resp = (
            client.table("searches")
            .delete()
            .eq("id", job_search_id)
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="jobs"))
            .select("id")
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete job search."
        ) from e
    row = _first_updated_row(resp)
    if not row or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job search not found.")
    return {"ok": True}


@router.post("/users/{target_user_id}/post-search/run", response_model=PostSearchRunResponse)
def admin_start_post_search_run(
    target_user_id: str,
    req: AdminPostSearchStartRequest,
    admin_user_id: str = Depends(require_admin_user_id),
) -> PostSearchRunResponse:
    client = _get_service_client()

    post_search_id = (req.post_search_id or "").strip() or None
    if post_search_id:
        try:
            resp = (
                client.table("searches")
                .select("id,search_type_id")
                .eq("id", post_search_id)
                .eq("user_id", target_user_id)
                .eq("search_type_id", _search_type_id(client=client, code="posts"))
                .maybe_single()
                .execute()
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load post search."
            ) from e
        row = getattr(resp, "data", None)
        if not isinstance(row, dict) or not row.get("id"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post search not found.")
    else:
        # Backward-compatible default: pick the oldest post_search for this user.
        try:
            resp = (
                client.table("searches")
                .select("id")
                .eq("user_id", target_user_id)
                .eq("search_type_id", _search_type_id(client=client, code="posts"))
                .order("created_at", desc=False)
                .limit(1)
                .maybe_single()
                .execute()
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load post search."
            ) from e
        row = getattr(resp, "data", None)
        if not isinstance(row, dict) or not row.get("id"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post search not found.")
        post_search_id = str(row.get("id"))

    _ensure_not_blocked_and_increment_counter(user_id=target_user_id)
    sess = start_post_search_session(
        sessions=_admin_sessions,
        user_id=target_user_id,
        post_search_id=post_search_id,
        limit=req.limit,
        account_label=req.account_label,
        initiated_by="admin",
        admin_actor_id=admin_user_id,
    )
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


@router.post("/users/{target_user_id}/job-search/run", response_model=JobSearchRunResponse)
def admin_start_job_search_run(
    target_user_id: str,
    req: JobSearchStartRequest,
    admin_user_id: str = Depends(require_admin_user_id),
) -> JobSearchRunResponse:
    client = _get_service_client()

    _ensure_not_blocked(user_id=target_user_id)

    try:
        resp = (
            client.table("searches")
            .select("id,search_type_id")
            .eq("id", req.job_search_id)
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="jobs"))
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load job search.") from e
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job search not found.")

    sess = start_job_search_session(
        sessions=_admin_job_sessions,
        user_id=target_user_id,
        job_search_id=req.job_search_id,
        limit=req.limit,
        account_label=req.account_label,
        initiated_by="admin",
        admin_actor_id=admin_user_id,
    )
    return JobSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


@router.get("/users/{target_user_id}/post-searches", response_model=list[AdminPostSearchRow])
def list_user_post_searches(
    target_user_id: str, _: str = Depends(require_admin_user_id)
) -> list[AdminPostSearchRow]:
    client = _get_service_client()
    try:
        resp = (
            client.table("searches")
            .select("id,user_id,title,search_tariff_id,email_report_enabled,email_report_format,status,last_run_at,created_at")
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="posts"))
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load post searches."
        ) from e
    rows_raw = getattr(resp, "data", None)
    rows: list[dict[str, Any]] = (
        [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []
    )
    return [AdminPostSearchRow(**r) for r in rows if r.get("id")]


@router.patch("/users/{target_user_id}/post-searches/{post_search_id}", response_model=AdminPostSearchRow)
def update_user_post_search(
    target_user_id: str,
    post_search_id: str,
    body: AdminPostSearchUpdate,
    _: str = Depends(require_admin_user_id),
) -> AdminPostSearchRow:
    client = _get_service_client()
    payload: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if "search_tariff_id" in body.model_fields_set:
        payload["search_tariff_id"] = _to_nullable_trimmed_string(body.search_tariff_id)
    if "email_report_enabled" in body.model_fields_set:
        payload["email_report_enabled"] = bool(body.email_report_enabled)
    if "email_report_format" in body.model_fields_set:
        payload["email_report_format"] = _validate_email_report_format(body.email_report_format) or "none"

    wants_email = bool(payload.get("email_report_enabled") is True)
    wants_format = bool(
        ("email_report_format" in payload)
        and isinstance(payload.get("email_report_format"), str)
        and payload.get("email_report_format") != "none"
    )
    if wants_email or wants_format:
        effective_tariff_id: str | None = None
        if "search_tariff_id" in payload:
            effective_tariff_id = payload.get("search_tariff_id") if isinstance(payload.get("search_tariff_id"), str) else None
        else:
            try:
                st = (
                    client.table("searches")
                    .select("search_tariff_id")
                    .eq("id", post_search_id)
                    .eq("user_id", target_user_id)
                    .eq("search_type_id", _search_type_id(client=client, code="posts"))
                    .maybe_single()
                    .execute()
                )
                row = getattr(st, "data", None)
                effective_tariff_id = row.get("search_tariff_id") if isinstance(row, dict) else None
            except Exception:
                effective_tariff_id = None

        if not _resolve_tariff_email_reports_enabled(client=client, tariff_id=effective_tariff_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tariff does not allow email reports.",
            )

    try:
        resp = (
            client.table("searches")
            .update(payload)
            .eq("id", post_search_id)
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="posts"))
            .select("id,user_id,title,search_tariff_id,email_report_enabled,email_report_format,status,last_run_at,created_at")
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update post search."
        ) from e
    row = _first_updated_row(resp)
    if not row or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post search not found.")
    return AdminPostSearchRow(**row)


@router.delete("/users/{target_user_id}/post-searches/{post_search_id}")
def delete_user_post_search(
    target_user_id: str,
    post_search_id: str,
    _: str = Depends(require_admin_user_id),
) -> dict[str, Any]:
    client = _get_service_client()
    try:
        resp = (
            client.table("searches")
            .delete()
            .eq("id", post_search_id)
            .eq("user_id", target_user_id)
            .eq("search_type_id", _search_type_id(client=client, code="posts"))
            .select("id")
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete post search."
        ) from e
    row = _first_updated_row(resp)
    if not row or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post search not found.")
    return {"ok": True}


@router.get("/search-runs", response_model=AdminSearchRunsListResponse)
def list_search_runs(
    user_id: str | None = None,
    kind: str | None = None,
    post_search_id: str | None = None,
    job_search_id: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(require_admin_user_id),
) -> AdminSearchRunsListResponse:
    from storage.domain.pulse.search_runs import SearchRunRepository  # type: ignore[import-not-found]

    kind_val = kind if kind in ("post", "job") else None
    status_val = status if status in ("running", "done", "error") else None
    order_val = "asc" if order == "asc" else "desc"

    repo = SearchRunRepository(_get_service_client())
    rows, total = repo.list_for_admin(
        user_id=user_id,
        kind=kind_val,  # type: ignore[arg-type]
        post_search_id=post_search_id,
        job_search_id=job_search_id,
        status=status_val,  # type: ignore[arg-type]
        date_from=date_from,
        date_to=date_to,
        order=order_val,
        limit=limit,
        offset=offset,
    )

    uids = list({str(r.get("user_id")) for r in rows if r.get("user_id")})
    names: dict[str, str | None] = {}
    if uids:
        try:
            prof = (
                _get_service_client()
                .table("user_profiles")
                .select("id,full_name")
                .in_("id", uids)
                .execute()
            )
            data = getattr(prof, "data", None)
            if isinstance(data, list):
                for p in data:
                    if isinstance(p, dict) and p.get("id"):
                        names[str(p["id"])] = p.get("full_name") if isinstance(p.get("full_name"), str) else None
        except Exception:
            names = {}

    items: list[AdminSearchRunRow] = []
    for r in rows:
        uid = str(r.get("user_id") or "")
        items.append(
            AdminSearchRunRow(
                **{
                    **r,
                    "user_email": None,
                    "user_full_name": names.get(uid),
                }
            )
        )

    return AdminSearchRunsListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/searches", response_model=AdminSearchesListResponse)
def list_searches(
    user_id: str | None = None,
    type: str | None = None,  # noqa: A002
    status: str | None = None,
    search_tariff_id: str | None = None,
    email_report_enabled: bool | None = None,
    q: str | None = None,
    order_by: str = "created_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(require_admin_user_id),
) -> AdminSearchesListResponse:
    client = _get_service_client()

    type_val = type if type in ("jobs", "posts") else None
    status_val = status if status in ("active", "paused") else None
    order_val = "asc" if order == "asc" else "desc"
    order_by_val = order_by if order_by in ("created_at", "updated_at", "last_run_at", "title") else "created_at"
    limit_val = max(1, min(200, int(limit)))
    offset_val = max(0, int(offset))

    sel = (
        "id,user_id,title,status,last_run_at,search_tariff_id,email_report_enabled,email_report_format,"
        "search_query,location,linkedin_filters,account_label,created_at,updated_at,"
        "search_types!inner(code),prompts(id,search_id,role,body,created_at,updated_at)"
    )
    req = client.table("searches").select(sel, count="exact")
    if isinstance(user_id, str) and user_id.strip():
        req = req.eq("user_id", user_id.strip())
    if type_val:
        req = req.eq("search_types.code", type_val)
    if status_val:
        req = req.eq("status", status_val)
    if isinstance(search_tariff_id, str) and search_tariff_id.strip():
        req = req.eq("search_tariff_id", search_tariff_id.strip())
    if email_report_enabled is True:
        req = req.eq("email_report_enabled", True)
    if email_report_enabled is False:
        req = req.eq("email_report_enabled", False)
    if isinstance(q, str) and (qs := q.strip()):
        req = req.ilike("title", f"%{qs}%")

    req = req.order(order_by_val, desc=(order_val == "desc")).range(offset_val, offset_val + limit_val - 1)
    try:
        resp = req.execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load searches.") from e

    total = int(getattr(resp, "count", None) or 0)
    rows_raw = getattr(resp, "data", None)
    rows: list[dict[str, Any]] = (
        [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []
    )
    uids = list({str(r.get("user_id")) for r in rows if r.get("user_id")})
    names_by_id = _load_user_names(client=client, user_ids=uids)

    items: list[AdminSearchRow] = []
    for r in rows:
        mapped = _admin_search_row_from_search(search_row=r)
        uid = str(mapped.get("user_id") or "")
        mapped["user_full_name"] = names_by_id.get(uid)
        mapped["user_email"] = None
        items.append(AdminSearchRow(**mapped))
    return AdminSearchesListResponse(items=items, total=total, limit=limit_val, offset=offset_val)


@router.patch("/searches/{search_id}", response_model=AdminSearchRow)
def update_search(
    search_id: str,
    body: AdminSearchUpdate,
    _: str = Depends(require_admin_user_id),
) -> AdminSearchRow:
    client = _get_service_client()

    # Load search + type
    try:
        base = (
            client.table("searches")
            .select("id,user_id,search_tariff_id,search_types!inner(code)")
            .eq("id", search_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load search.") from e
    row = getattr(base, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found.")
    st = row.get("search_types")
    search_type_code = st.get("code") if isinstance(st, dict) else None
    if search_type_code not in ("jobs", "posts"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid search type.")

    payload: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

    title = _require_non_empty_string(body.title, field="title")
    status_val = _to_nullable_trimmed_string(body.status)
    tariff_id = _to_nullable_trimmed_string(body.search_tariff_id)
    email_report_format = _validate_email_report_format(body.email_report_format)

    if title is not None:
        payload["title"] = title
    if body.status is not None:
        if status_val not in ("active", "paused", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status.")
        payload["status"] = status_val
    if "search_tariff_id" in body.model_fields_set:
        payload["search_tariff_id"] = tariff_id
    if "email_report_enabled" in body.model_fields_set:
        payload["email_report_enabled"] = bool(body.email_report_enabled)
    if "email_report_format" in body.model_fields_set:
        payload["email_report_format"] = email_report_format or "none"

    # Type-specific fields
    if search_type_code == "jobs":
        if body.account_label is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account_label is posts-only.")
        if body.search_query is not None:
            payload["search_query"] = _require_non_empty_string(body.search_query, field="search_query")
        if body.location is not None:
            payload["location"] = _to_nullable_trimmed_string(body.location)
        if body.linkedin_filters is not None:
            payload["linkedin_filters"] = body.linkedin_filters
        if body.search_prompt is not None or body.comment_prompt is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Post prompts are not allowed for jobs.")
    else:
        # posts
        if body.search_query is not None or body.location is not None or body.linkedin_filters is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job fields are not allowed for posts.")
        if body.account_label is not None:
            payload["account_label"] = _to_nullable_trimmed_string(body.account_label)
        if body.filter_prompt is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filter_prompt is jobs-only.")

    # Enforce tariff capability for email reports.
    wants_email = bool(payload.get("email_report_enabled") is True)
    wants_format = bool(
        ("email_report_format" in payload)
        and isinstance(payload.get("email_report_format"), str)
        and payload.get("email_report_format") != "none"
    )
    if wants_email or wants_format:
        effective_tariff_id = payload.get("search_tariff_id") if "search_tariff_id" in payload else row.get("search_tariff_id")
        effective_tariff_id = effective_tariff_id if isinstance(effective_tariff_id, str) else None
        if not _resolve_tariff_email_reports_enabled(client=client, tariff_id=effective_tariff_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tariff does not allow email reports.")

    # Prompt updates
    filter_prompt_to_save = _validate_job_search_filter_prompt(body.filter_prompt) if search_type_code == "jobs" else None

    post_search_prompt_to_save: str | None = None
    post_comment_prompt_to_save: str | None = None
    post_comment_delete = False
    if search_type_code == "posts" and ("search_prompt" in body.model_fields_set or "comment_prompt" in body.model_fields_set):
        # Load existing prompts if needed for validation.
        try:
            p_resp = client.table("prompts").select("role,body").eq("search_id", search_id).execute()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load prompts.") from e
        p_raw = getattr(p_resp, "data", None)
        p_rows = [p for p in p_raw if isinstance(p, dict)] if isinstance(p_raw, list) else []
        existing_search_prompt = next((p.get("body") for p in p_rows if p.get("role") == "search" and isinstance(p.get("body"), str)), None)
        existing_comment_prompt = next((p.get("body") for p in p_rows if p.get("role") == "comment" and isinstance(p.get("body"), str)), None)

        next_search_prompt = body.search_prompt if "search_prompt" in body.model_fields_set else existing_search_prompt
        next_comment_prompt = body.comment_prompt if "comment_prompt" in body.model_fields_set else existing_comment_prompt

        # comment_prompt may be explicitly cleared with empty string / None
        if "comment_prompt" in body.model_fields_set and (next_comment_prompt is None or (isinstance(next_comment_prompt, str) and not next_comment_prompt.strip())):
            post_comment_delete = True
            next_comment_prompt = None

        s_valid, c_valid = _validate_prompts(
            search_prompt=next_search_prompt if isinstance(next_search_prompt, str) else None,
            comment_prompt=next_comment_prompt if isinstance(next_comment_prompt, str) else None,
        )
        if "search_prompt" in body.model_fields_set:
            post_search_prompt_to_save = s_valid
        if "comment_prompt" in body.model_fields_set:
            post_comment_prompt_to_save = c_valid

    # Update search row
    try:
        upd = (
            client.table("searches")
            .update(payload)
            .eq("id", search_id)
            .select(
                "id,user_id,title,status,last_run_at,search_tariff_id,email_report_enabled,email_report_format,"
                "search_query,location,linkedin_filters,account_label,created_at,updated_at,"
                "search_types!inner(code),prompts(id,search_id,role,body,created_at,updated_at)"
            )
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update search.") from e
    updated_row = getattr(upd, "data", None)
    if not isinstance(updated_row, dict) or not updated_row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found.")

    # Apply prompt changes after search update (same strategy as per-user handlers).
    if search_type_code == "jobs" and filter_prompt_to_save is not None:
        try:
            client.table("prompts").upsert(
                [{"search_id": search_id, "role": "filter", "body": filter_prompt_to_save}],
                on_conflict="search_id,role",
            ).execute()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update prompt.") from e

    if search_type_code == "posts":
        if post_search_prompt_to_save is not None:
            try:
                client.table("prompts").upsert(
                    [{"search_id": search_id, "role": "search", "body": post_search_prompt_to_save}],
                    on_conflict="search_id,role",
                ).execute()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update prompt.") from e
        if post_comment_delete:
            try:
                client.table("prompts").delete().eq("search_id", search_id).eq("role", "comment").execute()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete prompt.") from e
        elif post_comment_prompt_to_save is not None:
            try:
                client.table("prompts").upsert(
                    [{"search_id": search_id, "role": "comment", "body": post_comment_prompt_to_save}],
                    on_conflict="search_id,role",
                ).execute()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update prompt.") from e

    # Re-fetch to include updated prompts in response.
    try:
        fresh = (
            client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,search_tariff_id,email_report_enabled,email_report_format,"
                "search_query,location,linkedin_filters,account_label,created_at,updated_at,"
                "search_types!inner(code),prompts(id,search_id,role,body,created_at,updated_at)"
            )
            .eq("id", search_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load search.") from e
    out = getattr(fresh, "data", None)
    if not isinstance(out, dict) or not out.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found.")

    mapped = _admin_search_row_from_search(search_row=out)
    uid = str(mapped.get("user_id") or "")
    mapped["user_full_name"] = _load_user_names(client=client, user_ids=[uid]).get(uid)
    mapped["user_email"] = None
    return AdminSearchRow(**mapped)


@router.get("/prompts", response_model=AdminPromptsListResponse)
def list_prompts(
    user_id: str | None = None,
    search_id: str | None = None,
    type: str | None = None,  # noqa: A002
    role: str | None = None,
    q: str | None = None,
    order_by: str = "updated_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(require_admin_user_id),
) -> AdminPromptsListResponse:
    client = _get_service_client()
    type_val = type if type in ("jobs", "posts") else None
    role_val = role if role in ("filter", "search", "comment") else None
    order_val = "asc" if order == "asc" else "desc"
    order_by_val = order_by if order_by in ("created_at", "updated_at", "role") else "updated_at"
    limit_val = max(1, min(200, int(limit)))
    offset_val = max(0, int(offset))

    sel = (
        "id,search_id,role,body,created_at,updated_at,"
        "searches!inner(id,user_id,title,search_type_id,search_types!inner(code))"
    )
    req = client.table("prompts").select(sel, count="exact")
    if isinstance(search_id, str) and search_id.strip():
        req = req.eq("search_id", search_id.strip())
    if isinstance(user_id, str) and user_id.strip():
        req = req.eq("searches.user_id", user_id.strip())
    if type_val:
        req = req.eq("searches.search_types.code", type_val)
    if role_val:
        req = req.eq("role", role_val)
    if isinstance(q, str) and (qs := q.strip()):
        req = req.ilike("body", f"%{qs}%")

    req = req.order(order_by_val, desc=(order_val == "desc")).range(offset_val, offset_val + limit_val - 1)
    try:
        resp = req.execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load prompts.") from e

    total = int(getattr(resp, "count", None) or 0)
    rows_raw = getattr(resp, "data", None)
    rows: list[dict[str, Any]] = (
        [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []
    )

    uids: list[str] = []
    items: list[AdminPromptRow] = []
    for r in rows:
        s = r.get("searches")
        if not isinstance(s, dict):
            continue
        uid = str(s.get("user_id") or "")
        if uid:
            uids.append(uid)
        st = s.get("search_types")
        code = st.get("code") if isinstance(st, dict) else None
        items.append(
            AdminPromptRow(
                id=str(r.get("id") or ""),
                search_id=str(r.get("search_id") or ""),
                role=str(r.get("role") or ""),
                body=str(r.get("body") or ""),
                created_at=r.get("created_at"),
                updated_at=r.get("updated_at"),
                user_id=uid,
                search_title=str(s.get("title") or ""),
                search_type_code=str(code or ""),
                user_full_name=None,
                user_email=None,
            )
        )

    names_by_id = _load_user_names(client=client, user_ids=list({u for u in uids if u}))
    out_items: list[AdminPromptRow] = []
    for it in items:
        out_items.append(
            AdminPromptRow(
                **{
                    **it.model_dump(),
                    "user_full_name": names_by_id.get(it.user_id),
                    "user_email": None,
                }
            )
        )
    return AdminPromptsListResponse(items=out_items, total=total, limit=limit_val, offset=offset_val)


@router.patch("/prompts/{prompt_id}", response_model=AdminPromptRow)
def update_prompt(
    prompt_id: str,
    body: AdminPromptUpdate,
    _: str = Depends(require_admin_user_id),
) -> AdminPromptRow:
    client = _get_service_client()
    # Load prompt + context
    try:
        resp = (
            client.table("prompts")
            .select("id,search_id,role,body,created_at,updated_at,searches!inner(id,user_id,title,search_types!inner(code))")
            .eq("id", prompt_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load prompt.") from e
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found.")
    role_val = row.get("role")
    if role_val not in ("filter", "search", "comment"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prompt role.")
    s = row.get("searches")
    if not isinstance(s, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prompt context.")
    st = s.get("search_types")
    code = st.get("code") if isinstance(st, dict) else None
    search_type_code = str(code or "")

    text = body.body if isinstance(body.body, str) else ""
    text = text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt body must be non-empty.")

    # Validate body according to role/type.
    if role_val == "filter":
        _validate_job_search_filter_prompt(text)
        if search_type_code != "jobs":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filter prompt must belong to jobs search.")
    elif role_val == "search":
        _validate_prompts(search_prompt=text, comment_prompt=None)
        if search_type_code != "posts":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="search prompt must belong to posts search.")
    else:
        # comment
        if search_type_code != "posts":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="comment prompt must belong to posts search.")
        if missing := _missing_markers(text, _COMMENT_REQUIRED_MARKERS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Промпт комментария должен содержать маркеры: {', '.join(missing)}.",
            )

    now = datetime.now(timezone.utc).isoformat()
    try:
        upd = (
            client.table("prompts")
            .update({"body": text, "updated_at": now})
            .eq("id", prompt_id)
            .select("id,search_id,role,body,created_at,updated_at,searches!inner(id,user_id,title,search_types!inner(code))")
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update prompt.") from e
    out = getattr(upd, "data", None)
    if not isinstance(out, dict) or not out.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found.")
    s2 = out.get("searches") if isinstance(out.get("searches"), dict) else s
    uid = str(s2.get("user_id") or "")
    st2 = s2.get("search_types")
    code2 = st2.get("code") if isinstance(st2, dict) else None
    full_name = _load_user_names(client=client, user_ids=[uid]).get(uid)
    return AdminPromptRow(
        id=str(out.get("id") or ""),
        search_id=str(out.get("search_id") or ""),
        role=str(out.get("role") or ""),
        body=str(out.get("body") or ""),
        created_at=out.get("created_at"),
        updated_at=out.get("updated_at"),
        user_id=uid,
        search_title=str(s2.get("title") or ""),
        search_type_code=str(code2 or ""),
        user_full_name=full_name,
        user_email=None,
    )


@router.get("/users/{target_user_id}/job-search/run/{session_id}", response_model=JobSearchRunResponse)
def admin_get_job_search_status(
    target_user_id: str,
    session_id: str,
    _: str = Depends(require_admin_user_id),
) -> JobSearchRunResponse:
    sess = _admin_job_sessions.get(user_id=target_user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return JobSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


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

