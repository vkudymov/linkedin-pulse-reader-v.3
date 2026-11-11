from __future__ import annotations

import re
from contextlib import suppress
from typing import Any

from playwright.sync_api import Locator, Page

from linkedin_search_people.models.person import Person
from linkedin_search_people.parsing.people_parser import (
    clean_headline,
    clean_person_name,
    extract_avatar_url,
    extract_public_id,
    normalize_profile_url,
)


def _text(loc: Locator) -> str:
    with suppress(Exception):
        t = (loc.inner_text() or "").strip()
        if t:
            return re.sub(r"\s+", " ", t)
    return ""


def _section_text(page: Page, headings: tuple[str, ...]) -> str:
    for heading in headings:
        loc = page.locator(
            f"section:has(h2:has-text('{heading}')), "
            f"section:has(span:has-text('{heading}')), "
            f"div:has(> h2:has-text('{heading}'))"
        ).first
        blob = _text(loc)
        if blob:
            # Drop the heading itself.
            for h in headings:
                if blob.lower().startswith(h.lower()):
                    blob = blob[len(h) :].strip()
            return blob
    return ""


def _skills(page: Page) -> tuple[str, ...]:
    skills: list[str] = []
    seen: set[str] = set()
    selectors = (
        "a[href*='/details/skills'] span[aria-hidden='true']",
        "section:has(#skills) span[aria-hidden='true']",
        "div.pvs-list__outer-container span.hoverable-link-text",
        "a[data-field='skill_card_skill_topic'] span[aria-hidden='true']",
    )
    for sel in selectors:
        loc = page.locator(sel)
        with suppress(Exception):
            n = min(loc.count(), 40)
            for i in range(n):
                raw = _text(loc.nth(i))
                name = raw.strip()
                if not name or len(name) > 80:
                    continue
                key = name.casefold()
                if key in seen:
                    continue
                if key in {"skills", "навыки", "show all", "показать все"}:
                    continue
                seen.add(key)
                skills.append(name)
            if skills:
                break
    return tuple(skills[:25])


def _list_items(page: Page, headings: tuple[str, ...], *, kind: str) -> tuple[dict[str, Any], ...]:
    items: list[dict[str, Any]] = []
    for heading in headings:
        root = page.locator(
            f"section:has(h2:has-text('{heading}')), section:has(#experience), section:has(#education)"
        ).first
        loc = root.locator("li, div.pvs-list__paged-list-item")
        with suppress(Exception):
            n = min(loc.count(), 12)
            for i in range(n):
                blob = _text(loc.nth(i))
                if not blob or len(blob) < 3:
                    continue
                title = blob.split(" · ")[0][:180]
                items.append({"kind": kind, "title": title, "text": blob[:500]})
            if items:
                break
    return tuple(items)


class ProfileParser:
    def parse_profile(self, page: Page, *, fallback_url: str | None = None) -> Person:
        url = normalize_profile_url(page.url) or normalize_profile_url(fallback_url)
        public_id = extract_public_id(url)

        name = ""
        for sel in ("h1", "h1.text-heading-xlarge", "main h1"):
            name = clean_person_name(_text(page.locator(sel).first)) or ""
            if name:
                break

        headline = ""
        for sel in (
            "div.text-body-medium.break-words",
            ".pv-text-details__left-panel .text-body-medium",
            "div.ph5 div.text-body-medium",
        ):
            headline = _text(page.locator(sel).first)
            if headline and headline != name:
                break
            headline = ""
        headline = clean_headline(headline, location=None, name=name) or headline or None

        location = ""
        for sel in (
            "span.text-body-small.inline.t-black--light.break-words",
            "div.pv-text-details__left-panel span.text-body-small",
            "span.text-body-small.t-black--light",
        ):
            location = _text(page.locator(sel).first)
            if location and location not in {name, headline}:
                break
            location = ""

        about = _section_text(page, ("About", "О себе", "Info", "Сведения"))
        skills = _skills(page)
        experience = _list_items(page, ("Experience", "Опыт работы"), kind="experience")
        education = _list_items(page, ("Education", "Образование"), kind="education")

        current_company = None
        if experience:
            current_company = str(experience[0].get("title") or "") or None

        avatar_url = None
        for sel in (
            "main .pv-top-card",
            "main .pv-top-card-profile-picture",
            "main section.artdeco-card",
            "main",
        ):
            scope = page.locator(sel).first
            with suppress(Exception):
                if scope.count() == 0:
                    continue
                avatar_url = extract_avatar_url(scope, public_id=public_id)
                if avatar_url:
                    break

        return Person(
            public_id=public_id,
            profile_url=url,
            full_name=name or None,
            avatar_url=avatar_url,
            headline=headline or None,
            location=location or None,
            about=about or None,
            skills=skills,
            current_company=current_company,
            experience=experience,
            education=education,
        )
