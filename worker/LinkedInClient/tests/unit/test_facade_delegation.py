from linkedin_client import LinkedInClient
from linkedin_client.exceptions import BrowserLifecycleError


def test_facade_search_methods_require_an_open_session() -> None:
    client = LinkedInClient(headless=True)
    for call in (
        lambda: client.fetch_jobs(keywords="ABAP"),
        lambda: client.fetch_posts(limit=1),
        lambda: client.read_posts(limit=1),
    ):
        try:
            call()
        except BrowserLifecycleError as exc:
            assert "context manager" in str(exc)
        else:
            raise AssertionError("expected BrowserLifecycleError")
