from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from session_snapshot import (
    SessionLoggedOutError,
    export_session,
    from_playwright_cookies,
    has_auth_cookie,
    is_logged_out,
    is_snapshot_payload,
    load_snapshot,
    merge_snapshot,
    playwright_list_to_snapshot,
    restore_session,
    seed_origin_storage,
    should_save_back,
    to_playwright_cookies,
)
from session_snapshot.convert import chrome_cookie_to_playwright


def test_samesite_and_expiration_round_trip() -> None:
    chrome = {
        "name": "li_at",
        "value": "token",
        "domain": ".linkedin.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "expirationDate": 1735689600.9,
    }
    pw = chrome_cookie_to_playwright(chrome)
    assert pw["sameSite"] == "None"
    assert pw["expires"] == 1735689600
    assert "url" not in pw
    exported = from_playwright_cookies([pw])
    assert exported[0]["expirationDate"] == 1735689600.0
    assert exported[0]["sameSite"] == "None"


def test_domain_keeps_domain_and_path_not_url() -> None:
    pw = to_playwright_cookies(
        [{"name": "li_at", "value": "x", "domain": ".www.linkedin.com", "path": "/feed"}]
    )[0]
    assert pw["domain"] == ".www.linkedin.com"
    assert pw["path"] == "/feed"
    assert "url" not in pw


def test_cookie_without_domain_uses_url() -> None:
    # GOLD: url is built from domain without a leading dot. If `domain` is absent,
    # cookie_url is None and neither domain nor url is set. Pulse never invents a host.
    pw = chrome_cookie_to_playwright({"name": "foo", "value": "bar", "secure": True, "path": "/x"})
    assert "domain" not in pw
    assert "url" not in pw

    # Host-only-style: domain without leading dot still uses domain+path, not url-only.
    with_host = chrome_cookie_to_playwright(
        {"name": "foo", "value": "bar", "domain": "www.linkedin.com", "path": "/", "secure": True}
    )
    assert with_host["domain"] == "www.linkedin.com"
    assert with_host["path"] == "/"
    assert "url" not in with_host


def test_unspecified_samesite_omitted() -> None:
    pw = chrome_cookie_to_playwright(
        {
            "name": "n",
            "value": "v",
            "domain": ".linkedin.com",
            "sameSite": "unspecified",
        }
    )
    assert "sameSite" not in pw


def test_seed_origin_storage_goto_commit_only_when_keys() -> None:
    page = MagicMock()
    seed_origin_storage(
        page,
        {
            "origin": "https://www.linkedin.com",
            "localStorage": {"k": "v"},
            "sessionStorage": {},
        },
    )
    page.goto.assert_called_once_with("https://www.linkedin.com", wait_until="commit")
    page.evaluate.assert_called_once()

    page.reset_mock()
    seed_origin_storage(
        page,
        {
            "origin": "https://www.linkedin.com",
            "localStorage": {},
            "sessionStorage": {},
        },
    )
    page.goto.assert_not_called()
    page.evaluate.assert_not_called()


def test_empty_legacy_storage_restore_add_cookies_no_goto() -> None:
    context = MagicMock()
    page = MagicMock()
    snapshot = playwright_list_to_snapshot(
        [{"name": "li_at", "value": "tok", "domain": ".linkedin.com", "path": "/"}]
    )
    restore_session(context, page, snapshot)
    context.add_cookies.assert_called_once()
    args = context.add_cookies.call_args[0][0]
    assert args[0]["name"] == "li_at"
    assert args[0]["value"] == "tok"
    assert args[0]["domain"] == ".linkedin.com"
    page.goto.assert_not_called()


def test_merge_replaces_cookies_keeps_browser_viewport_updates_tab() -> None:
    base = {
        "cookies": [{"name": "old", "value": "1"}],
        "browser": {"userAgent": "UA", "timeZone": "Europe/Moscow"},
        "viewport": {"innerWidth": 1280, "innerHeight": 720},
        "tab": {"title": "keep-me"},
    }
    merged = merge_snapshot(
        base,
        cookies=[{"name": "new", "value": "2", "domain": ".linkedin.com", "path": "/"}],
        storage={
            "origin": "https://www.linkedin.com",
            "localStorage": {"a": "b"},
            "sessionStorage": {},
        },
        tab_url="https://www.linkedin.com/feed/",
        browser_timezone=None,
    )
    assert merged["cookies"][0]["name"] == "new"
    assert merged["browser"]["userAgent"] == "UA"
    assert merged["browser"]["timeZone"] == "Europe/Moscow"
    assert merged["viewport"]["innerWidth"] == 1280
    assert merged["tab"]["url"] == "https://www.linkedin.com/feed/"
    assert merged["tab"]["title"] == "keep-me"


def test_merge_does_not_overwrite_timezone_when_none() -> None:
    base = {"browser": {"timeZone": "Europe/Moscow"}}
    merged = merge_snapshot(
        base,
        cookies=[{"name": "n", "value": "v"}],
        storage={"origin": "", "localStorage": {}, "sessionStorage": {}},
        tab_url=None,
        browser_timezone=None,
    )
    assert merged["browser"]["timeZone"] == "Europe/Moscow"


@pytest.mark.parametrize(
    ("url", "logged_out"),
    [
        ("https://www.linkedin.com/login", True),
        ("https://www.linkedin.com/checkpoint/challenge", True),
        ("https://www.linkedin.com/authwall", True),
        ("https://www.linkedin.com/uas/login", True),
        ("https://www.linkedin.com/feed/", False),
    ],
)
def test_is_logged_out_hints(url: str, logged_out: bool) -> None:
    assert is_logged_out(url) is logged_out
    assert should_save_back(url) is (not logged_out)


def test_has_auth_cookie_li_at() -> None:
    assert has_auth_cookie([{"name": "li_at", "value": "abc"}]) is True
    assert has_auth_cookie([{"name": "JSESSIONID", "value": "x"}]) is False
    assert has_auth_cookie([{"name": "li_at", "value": ""}]) is False


def test_load_snapshot_from_list_dict_and_empty() -> None:
    from_list = load_snapshot(
        {"cookies_json": [{"name": "li_at", "value": "t", "domain": ".linkedin.com", "path": "/"}]}
    )
    assert from_list["diagnostics"]["source"] == "legacy_playwright_list"
    assert from_list["cookies"][0]["name"] == "li_at"

    full = {
        "cookies": [{"name": "li_at", "value": "z"}],
        "storage": {"origin": "https://www.linkedin.com", "localStorage": {}, "sessionStorage": {}},
    }
    assert load_snapshot({"session_snapshot": full})["cookies"][0]["value"] == "z"
    assert load_snapshot({"cookies_json": full})["cookies"][0]["value"] == "z"
    empty = load_snapshot({})
    assert empty["cookies"] == []
    assert is_snapshot_payload(full) is True
    assert is_snapshot_payload([]) is False


def test_playwright_list_round_trip_name_value_domain() -> None:
    original = [{"name": "li_at", "value": "tok", "domain": ".linkedin.com", "path": "/", "expires": 99}]
    snap = playwright_list_to_snapshot(original)
    restored = to_playwright_cookies(snap["cookies"])
    assert restored[0]["name"] == "li_at"
    assert restored[0]["value"] == "tok"
    assert restored[0]["domain"] == ".linkedin.com"


def test_export_session_raises_on_login_wall() -> None:
    context = MagicMock()
    page = MagicMock()
    page.url = "https://www.linkedin.com/login"
    with pytest.raises(SessionLoggedOutError):
        export_session(context, page, {"cookies": []})
    context.cookies.assert_not_called()
