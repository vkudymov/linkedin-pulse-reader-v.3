from __future__ import annotations

"""
RU: Human-like scrolling (low-level interaction utility).
    Этот модуль реализует имитацию “человеческой” прокрутки для LinkedIn страниц.
    Архитектурно это слой interaction utilities: он не знает о cookies, навигации, ожиданиях и парсинге,
    а работает только с уже созданным `page` Playwright.

RU: Зачем это нужно
    LinkedIn догружает контент лениво и использует эвристики против автоматизации. Выделение
    прокрутки в отдельный модуль позволяет централизованно тюнить поведение (дистанции/паузы)
    без влияния на бизнес-логику фич.

EN: Human-like scrolling (low-level interaction utility).
    This module implements “human-like” scrolling for LinkedIn pages.
    Architecturally, it is an interaction utilities layer: it does not handle cookies, navigation,
    waiting, or parsing, and operates only on an already-created Playwright `page`.

EN: Why it exists
    LinkedIn lazily loads content and applies anti-automation heuristics. Keeping scrolling in a
    dedicated module lets us tune behavior (distances/pauses) centrally without impacting feature logic.
"""

import random

from playwright.sync_api import Page


_SCROLL_METRICS_JS = """
() => {
  const docEl = document.documentElement;
  const root = document.scrollingElement || docEl;
  const canScrollRoot = (root.scrollHeight - root.clientHeight) > 4;
  if (canScrollRoot) {
    return [root.scrollTop || 0, root.scrollHeight || 0];
  }

  // LinkedIn часто использует вложенный scroll-container. Чтобы не зависеть от селекторов,
  // ищем "лучший" скроллируемый элемент эвристикой.
  let best = null;
  let bestScore = 0;

  const candidates = document.querySelectorAll("main, [role='main'], div, section");
  for (const el of candidates) {
    if (!(el instanceof HTMLElement)) continue;
    const sh = el.scrollHeight || 0;
    const ch = el.clientHeight || 0;
    const diff = sh - ch;
    if (diff <= 80) continue;
    const style = window.getComputedStyle(el);
    const oy = style.overflowY;
    if (oy !== "auto" && oy !== "scroll") continue;
    const score = diff + Math.min(200, (el.clientWidth || 0));
    if (score > bestScore) {
      bestScore = score;
      best = el;
    }
  }

  if (best) {
    return [best.scrollTop || 0, best.scrollHeight || 0];
  }

  return [root.scrollTop || 0, root.scrollHeight || 0];
}
"""

_SCROLL_BY_JS = """
(dy) => {
  const docEl = document.documentElement;
  const root = document.scrollingElement || docEl;
  const canScrollRoot = (root.scrollHeight - root.clientHeight) > 4;
  if (canScrollRoot) {
    root.scrollBy(0, dy);
    return true;
  }

  let best = null;
  let bestScore = 0;
  const candidates = document.querySelectorAll("main, [role='main'], div, section");
  for (const el of candidates) {
    if (!(el instanceof HTMLElement)) continue;
    const sh = el.scrollHeight || 0;
    const ch = el.clientHeight || 0;
    const diff = sh - ch;
    if (diff <= 80) continue;
    const style = window.getComputedStyle(el);
    const oy = style.overflowY;
    if (oy !== "auto" && oy !== "scroll") continue;
    const score = diff + Math.min(200, (el.clientWidth || 0));
    if (score > bestScore) {
      bestScore = score;
      best = el;
    }
  }

  if (best) {
    best.scrollBy(0, dy);
    return true;
  }

  window.scrollBy(0, dy);
  return false;
}
"""


def human_scroll(page: Page, *, steps: int) -> None:
    """
    RU: Прокрутить страницу вниз “как человек” в несколько шагов.
        Предназначено для безопасной догрузки контента. Функция не читает DOM и не парсит посты.

    EN: Scroll down in multiple “human-like” steps.
        Intended to safely trigger lazy-loading. This function does not read the DOM and does not parse posts.
    """
    if steps < 0:
        raise ValueError("steps must be >= 0")
    if steps == 0:
        return

    # EN: Ensure the page receives wheel/keyboard events.
    # RU: Гарантируем, что страница получит wheel/keyboard события.
    try:
        page.focus("body")
    except Exception:
        pass

    for _ in range(steps):
        # EN/RU: Use scrollTop as a generic progress signal (no DOM parsing).
        try:
            before = page.evaluate(_SCROLL_METRICS_JS)[0]
        except Exception:
            before = None

        delta_y = random.randint(300, 900)

        # Split a single scroll step into smaller wheel events for more natural cadence.
        chunks = random.randint(2, 5)
        per = max(1, int(delta_y / chunks))
        for _ in range(chunks):
            page.mouse.wheel(0, per)
            page.wait_for_timeout(random.randint(40, 140))

        # EN: If wheel didn't move the page, fallback to keyboard, then JS scrollBy.
        # RU: Если wheel не сдвинул страницу, делаем fallback на клавиатуру, затем JS scrollBy.
        try:
            after = page.evaluate(_SCROLL_METRICS_JS)[0]
        except Exception:
            after = None

        if before is not None and after is not None and after <= before:
            try:
                page.keyboard.press("PageDown")
                page.wait_for_timeout(random.randint(120, 260))
                after2 = page.evaluate(_SCROLL_METRICS_JS)[0]
            except Exception:
                after2 = after

            if before is not None and after2 is not None and after2 <= before:
                try:
                    page.evaluate(_SCROLL_BY_JS, random.randint(250, 750))
                except Exception:
                    pass

        page.wait_for_timeout(random.randint(450, 1800))

