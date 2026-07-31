from linkedin_client.parsing.author_extract import (
    _clean_author_name,
    _looks_like_author_name,
    _normalize_avatar_src,
)


def test_clean_author_name_strips_connection_degree() -> None:
    assert _clean_author_name("Jane Doe • 1st") == "Jane Doe"


def test_looks_like_author_name_rejects_urls() -> None:
    assert _looks_like_author_name("https://linkedin.com/in/jane") is False
    assert _looks_like_author_name("Jane Doe") is True


def test_normalize_avatar_src_accepts_profile_photo() -> None:
    url = "https://media.licdn.com/dms/image/v2/C5603AQH/example/profile-displayphoto-shrink_100_100/0/123"
    assert _normalize_avatar_src(url) == url


def test_normalize_avatar_src_rejects_ghost_placeholder() -> None:
    ghost = "https://static.licdn.com/aero-v1/sc/h/ghost-person.png"
    assert _normalize_avatar_src(ghost) is None
    assert _normalize_avatar_src(None) is None
    assert _normalize_avatar_src("data:image/png;base64,abc") is None
