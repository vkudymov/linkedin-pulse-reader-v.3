from __future__ import annotations

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class _FakeLocator:
    def __init__(self, page: "_FakePage", selector: str, *, count: int = 1) -> None:
        self._page = page
        self._selector = selector
        self._count = count

    def count(self) -> int:
        return self._count

    @property
    def first(self) -> "_FakeLocator":
        return self

    def fill(self, value: str) -> None:
        self._page.calls.append(("fill", self._selector, value))

    def click(self) -> None:
        self._page.calls.append(("click", self._selector, None))


class _FakeRoleLocator(_FakeLocator):
    pass


class _FakeKeyboard:
    def __init__(self, page: "_FakePage") -> None:
        self._page = page

    def press(self, key: str) -> None:
        self._page.calls.append(("press", key, None))


class _FakePage:
    def __init__(self) -> None:
        self.url = "https://www.linkedin.com/login"
        self.calls: list[tuple[str, str, object | None]] = []
        self.keyboard = _FakeKeyboard(self)

    def goto(self, url: str, wait_until: str) -> None:
        self.calls.append(("goto", url, wait_until))
        self.url = url

    def wait_for_selector(self, selector: str, timeout: int) -> None:
        self.calls.append(("wait_for_selector", selector, timeout))

    def locator(self, selector: str) -> _FakeLocator:
        # For submit selector we want it to exist by default.
        if selector == "button[type='submit']":
            return _FakeLocator(self, selector, count=1)
        if "form[action*='checkpoint']" in selector:
            return _FakeLocator(self, selector, count=0)
        return _FakeLocator(self, selector, count=1)

    def get_by_role(self, role: str, name) -> _FakeRoleLocator:  # type: ignore[no-untyped-def]
        # Always "find" a button for tests.
        return _FakeRoleLocator(self, f"role={role}", count=1)

    def get_by_text(self, name) -> _FakeLocator:  # type: ignore[no-untyped-def]
        return _FakeLocator(self, "text", count=1)

    def wait_for_url(self, pattern: str, timeout: int) -> None:
        raise PlaywrightTimeoutError("timeout")

    def wait_for_timeout(self, ms: int) -> None:
        self.calls.append(("wait_for_timeout", str(ms), None))


class _FakeContext:
    class _ExpectPage:
        def __init__(self, timeout: int) -> None:
            self._timeout = timeout

        def __enter__(self) -> "_FakeContext._ExpectPage":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            raise PlaywrightTimeoutError("no popup")

        @property
        def value(self):  # pragma: no cover
            raise AssertionError("popup should not be used in unit tests")

    def expect_page(self, timeout: int) -> "_FakeContext._ExpectPage":
        return _FakeContext._ExpectPage(timeout=timeout)


def test_email_password_flow_fills_and_submits(monkeypatch: pytest.MonkeyPatch) -> None:
    from linkedin_client.auth.email_password import (
        EmailPasswordLoginFlow,
        EmailPasswordLoginParams,
    )

    monkeypatch.setattr(
        "linkedin_client.auth.email_password.wait_for_session", lambda *_a, **_kw: None
    )

    page = _FakePage()
    ctx = _FakeContext()

    flow = EmailPasswordLoginFlow(
        timeout_ms=10_000,
        params=EmailPasswordLoginParams(identifier="user@example.com", password="pw"),
    )
    flow.run(page=page, context=ctx)  # type: ignore[arg-type]

    assert ("fill", "input#username, input[name='session_key']", "user@example.com") in page.calls
    assert ("fill", "input#password, input[name='session_password']", "pw") in page.calls
    assert ("click", "button[type='submit']", None) in page.calls


def test_email_password_flow_does_not_fill_without_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from linkedin_client.auth.email_password import (
        EmailPasswordLoginFlow,
        EmailPasswordLoginParams,
    )

    monkeypatch.setattr(
        "linkedin_client.auth.email_password.wait_for_session", lambda *_a, **_kw: None
    )

    page = _FakePage()
    ctx = _FakeContext()

    flow = EmailPasswordLoginFlow(
        timeout_ms=10_000,
        params=EmailPasswordLoginParams(identifier=None, password=None),
    )
    flow.run(page=page, context=ctx)  # type: ignore[arg-type]

    assert all(c[0] != "fill" for c in page.calls)


def test_wait_for_session_checkpoint_raises() -> None:
    from linkedin_client.auth.wait import SessionWaitConfig, wait_for_session
    from linkedin_client.exceptions import LoginCheckpointError

    page = _FakePage()
    page.url = "https://www.linkedin.com/checkpoint/challenge"

    with pytest.raises(LoginCheckpointError):
        wait_for_session(
            page,
            cfg=SessionWaitConfig(timeout_ms=10, raise_on_checkpoint=True),
        )  # type: ignore[arg-type]


def test_wait_for_session_timeout_raises() -> None:
    from linkedin_client.auth.wait import SessionWaitConfig, wait_for_session
    from linkedin_client.exceptions import LoginTimeoutError

    page = _FakePage()
    page.url = "https://www.linkedin.com/login"

    with pytest.raises(LoginTimeoutError):
        wait_for_session(page, cfg=SessionWaitConfig(timeout_ms=5))  # type: ignore[arg-type]


def test_client_login_uses_email_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    from linkedin_client import LinkedInClient, LinkedInClientConfig
    from linkedin_client.auth.methods import LoginMethod
    from linkedin_client.browser import BrowserConfig

    calls: list[tuple[str, object | None]] = []

    monkeypatch.setattr(
        "linkedin_client.client.extract_cookies",
        lambda _ctx: [{"name": "li_at", "value": "x", "domain": "linkedin.com"}],
    )

    def _email_run(self, page, context) -> None:  # type: ignore[no-untyped-def]
        calls.append(("email", getattr(self, "_params", None)))

    monkeypatch.setattr("linkedin_client.client.EmailPasswordLoginFlow.run", _email_run)

    cfg = LinkedInClientConfig(browser=BrowserConfig(headless=True, timeout_ms=1000))
    client = LinkedInClient(config=cfg)

    class _Handle:
        def __init__(self) -> None:
            self.context = object()
            self.page = _FakePage()

    client._entered = True  # type: ignore[attr-defined]
    client._initial_cookies = None  # type: ignore[attr-defined]
    client._manual_login_completed = False  # type: ignore[attr-defined]
    client._browser._handle = _Handle()  # type: ignore[attr-defined]

    cookies = client.login_and_get_cookies(
        method=LoginMethod.email, identifier="user@example.com", password="pw"
    )

    assert cookies and cookies[0]["name"] == "li_at"
    assert any(c[0] == "email" for c in calls)


def test_client_login_uses_social_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    from linkedin_client import LinkedInClient, LinkedInClientConfig
    from linkedin_client.auth.methods import LoginMethod
    from linkedin_client.browser import BrowserConfig

    calls: list[str] = []

    monkeypatch.setattr(
        "linkedin_client.client.extract_cookies",
        lambda _ctx: [{"name": "li_at", "value": "x", "domain": "linkedin.com"}],
    )

    def _social_run(self, page, context) -> None:  # type: ignore[no-untyped-def]
        calls.append("social")

    monkeypatch.setattr("linkedin_client.client.SocialLoginFlow.run", _social_run)

    cfg = LinkedInClientConfig(browser=BrowserConfig(headless=True, timeout_ms=1000))
    client = LinkedInClient(config=cfg)

    class _Handle:
        def __init__(self) -> None:
            self.context = object()
            self.page = _FakePage()

    client._entered = True  # type: ignore[attr-defined]
    client._initial_cookies = None  # type: ignore[attr-defined]
    client._manual_login_completed = False  # type: ignore[attr-defined]
    client._browser._handle = _Handle()  # type: ignore[attr-defined]

    cookies = client.login_and_get_cookies(method=LoginMethod.google)

    assert cookies and cookies[0]["name"] == "li_at"
    assert calls == ["social"]

