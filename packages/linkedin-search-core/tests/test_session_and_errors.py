from pathlib import Path

from linkedin_search_core import (
    BrowserLifecycleError,
    FeedLoadError,
    LinkedInClientConfig,
    LinkedInClientError,
    LinkedInSession,
    LoginRequiredError,
    UserIdentity,
)
from linkedin_search_core.loading.scroller import ScrollConfig


def test_errors_share_a_base_type() -> None:
    assert issubclass(BrowserLifecycleError, LinkedInClientError)
    assert issubclass(LoginRequiredError, LinkedInClientError)
    assert issubclass(FeedLoadError, LinkedInClientError)


def test_config_defaults() -> None:
    cfg = LinkedInClientConfig()
    assert cfg.feed_url == "https://www.linkedin.com/feed/"
    assert cfg.expand_truncated_text is True
    assert isinstance(cfg.scroll, ScrollConfig)


def test_user_identity_defaults() -> None:
    identity = UserIdentity()
    assert identity.profile_url is None
    assert identity.urn is None


def test_get_cookies_requires_an_open_session() -> None:
    session = LinkedInSession(headless=True)
    try:
        session.get_cookies()
    except BrowserLifecycleError as exc:
        assert "context manager" in str(exc)
    else:
        raise AssertionError("expected BrowserLifecycleError")


def test_core_does_not_import_feature_packages() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "linkedin_search_core"
    imports = []
    for path in root.rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                imports.append(stripped)
    joined = "\n".join(imports)
    assert "linkedin_search_jobs" not in joined
    assert "linkedin_search_posts" not in joined
