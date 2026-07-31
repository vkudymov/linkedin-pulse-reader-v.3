import pytest

from linkedin_client.loading.scroller import HumanScroller, ScrollConfig
from linkedin_client.loading import scroller as scroller_mod


class _FakePage:
    def __init__(self, metrics: list[tuple[int, int]]) -> None:
        self._metrics = metrics

    def evaluate(self, _script: str):
        if not self._metrics:
            raise RuntimeError("no more metrics")
        return self._metrics.pop(0)


def test_has_progress_scroll_top_increases() -> None:
    assert scroller_mod._has_progress((0, 1000), (10, 1000)) is True


def test_has_progress_scroll_height_increases() -> None:
    assert scroller_mod._has_progress((10, 1000), (10, 1200)) is True


def test_has_progress_no_change() -> None:
    assert scroller_mod._has_progress((10, 1000), (10, 1000)) is False


def test_scroll_batches_stops_on_stagnation(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid invoking real Playwright interactions in unit tests.
    monkeypatch.setattr(scroller_mod, "human_scroll", lambda _page, *, steps: None)

    cfg = ScrollConfig(max_scrolls=10, max_no_progress_scrolls=2)
    scroller = HumanScroller(config=cfg)

    # 1st batch: progress (0->100). Next two batches: no progress -> stop.
    page = _FakePage(
        metrics=[
            (0, 1000),
            (100, 1000),
            (100, 1000),
            (100, 1000),
            (100, 1000),
            (100, 1000),
        ]
    )

    progressed = scroller.scroll_batches(page=page, batches=10)
    assert progressed == 1

