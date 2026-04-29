import json
import os
import re

import pytest


_POSTS_JSON = "/Users/vladimirkudymov/Work/LinkedInClient/run/posts.json"
_POST_URN_RE = re.compile(r"^urn:li:(activity|ugcPost):\d+$")


def _load_posts() -> list[dict]:
    if not os.path.exists(_POSTS_JSON):
        pytest.skip(f"Missing {_POSTS_JSON}; run run/run.py first to generate it.")
    with open(_POSTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise AssertionError(f"Expected list in {_POSTS_JSON}, got {type(data).__name__}")
    return data


def test_posts_have_urn_and_post_url() -> None:
    """
    Regression test for:
    - post_url is null
    - urn is null/empty or non-activity (e.g. aggregate cards)
    """
    posts = _load_posts()

    null_post_url = [i for i, p in enumerate(posts) if not (p.get("post_url") or "").strip()]
    empty_urn = [i for i, p in enumerate(posts) if not (p.get("urn") or "").strip()]
    non_activity_urn = [
        i
        for i, p in enumerate(posts)
        if (u := (p.get("urn") or "").strip()) and not _POST_URN_RE.match(u)
    ]

    details = {
        "items": len(posts),
        "null_post_url": null_post_url[:20],
        "empty_urn": empty_urn[:20],
        "non_activity_urn": non_activity_urn[:20],
    }

    assert not non_activity_urn, f"Found non-post urn values: {details}"
    assert not empty_urn, f"Found empty urn values: {details}"
    assert not null_post_url, f"Found null post_url values: {details}"

