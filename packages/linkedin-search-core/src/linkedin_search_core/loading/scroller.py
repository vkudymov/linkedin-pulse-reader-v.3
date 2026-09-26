from __future__ import annotations

"""
RU: Human-like scrolling для догрузки ленты.
    Скролл вынесен в отдельный компонент, чтобы менять политику (шаги/паузы) независимо от ожиданий
    и парсинга. Прогресс измеряется selector-agnostic сигналами (scrollTop/scrollHeight).

EN: Human-like scrolling to load more feed content.
    Scrolling is isolated so the policy (steps/pauses) can evolve independently from waiting/parsing.
    Progress is measured via selector-agnostic signals (scrollTop/scrollHeight).
"""

from dataclasses import dataclass

from playwright.sync_api import Page

from ..scroll.human_scroll import human_scroll


@dataclass(frozen=True, slots=True)
class ScrollConfig:
    """
    RU: Конфигурация политики скролла (параметры “человечности” и стоп-условия).
    EN: Scrolling policy configuration (human-like parameters and stop conditions).
    """
    min_delta_y: int = 300
    max_delta_y: int = 800
    min_pause_ms: int = 450
    max_pause_ms: int = 1800

    max_scrolls: int = 40
    max_no_progress_scrolls: int = 4

    jitter_chance: float = 0.15
    jitter_delta_y: int = 120


class HumanScroller:
    """
    RU: Исполнитель политики скролла.
        Не парсит посты и не “понимает” их структуру — его задача догрузить DOM до нужного объёма.

    EN: Scrolling policy executor.
        Does not parse posts or depend on their structure — it only loads enough DOM content.
    """
    def __init__(self, config: ScrollConfig | None = None) -> None:
        self._cfg = config or ScrollConfig()

    def scroll_batch(self, *, page: Page) -> bool:
        """
        RU: Выполнить один “человеческий” scroll-батч без привязки к DOM-селекторам.
            Возвращает True, если зафиксирован прогресс по scrollTop/scrollHeight.

        EN: Perform a single human-like scroll batch without relying on DOM selectors.
            Returns True if progress is detected via scrollTop/scrollHeight signals.
        """
        before = _scroll_metrics(page)
        human_scroll(page, steps=1)
        after = _scroll_metrics(page)
        return _has_progress(before, after)

    def scroll_batches(self, *, page: Page, batches: int) -> int:
        """
        RU: Выполнить несколько батчей и остановиться на стагнации.
            Возвращает количество батчей, в которых был прогресс.

        EN: Perform multiple batches and stop on stagnation.
            Returns the number of batches that made progress.
        """
        if batches <= 0:
            return 0

        progressed = 0
        no_progress = 0
        for _ in range(min(batches, self._cfg.max_scrolls)):
            if self.scroll_batch(page=page):
                progressed += 1
                no_progress = 0
            else:
                no_progress += 1
                if no_progress >= self._cfg.max_no_progress_scrolls:
                    break

        return progressed


def _scroll_metrics(page: Page) -> tuple[int, int]:
    try:
        return page.evaluate(
            "() => {"
            "  const docEl = document.documentElement;"
            "  const root = document.scrollingElement || docEl;"
            "  const canScrollRoot = (root.scrollHeight - root.clientHeight) > 4;"
            "  if (canScrollRoot) { return [root.scrollTop || 0, root.scrollHeight || 0]; }"
            "  let best = null;"
            "  let bestScore = 0;"
            "  const candidates = document.querySelectorAll(\"main, [role='main'], div, section\");"
            "  for (const el of candidates) {"
            "    if (!(el instanceof HTMLElement)) continue;"
            "    const sh = el.scrollHeight || 0;"
            "    const ch = el.clientHeight || 0;"
            "    const diff = sh - ch;"
            "    if (diff <= 80) continue;"
            "    const style = window.getComputedStyle(el);"
            "    const oy = style.overflowY;"
            "    if (oy !== 'auto' && oy !== 'scroll') continue;"
            "    const score = diff + Math.min(200, (el.clientWidth || 0));"
            "    if (score > bestScore) { bestScore = score; best = el; }"
            "  }"
            "  if (best) { return [best.scrollTop || 0, best.scrollHeight || 0]; }"
            "  return [root.scrollTop || 0, root.scrollHeight || 0];"
            "}"
        )
    except Exception:
        return (0, 0)


def _has_progress(before: tuple[int, int], after: tuple[int, int]) -> bool:
    return after[0] > before[0] or after[1] > before[1]

