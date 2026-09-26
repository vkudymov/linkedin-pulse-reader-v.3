from pathlib import Path

from linkedin_search_core.exceptions import BrowserLifecycleError
from linkedin_search_posts import Author, Post, PostSearch
from linkedin_search_posts.models.post import merge_authors


class _ClosedSession:
    _entered = False


class _OpenSession:
    _entered = True


def test_post_model_and_author_merge() -> None:
    author = merge_authors(Author(name="Ada"), Author(name="Ada", headline="Engineer"))
    assert author is not None
    assert author.headline == "Engineer"
    post = Post(id="1", content="hello", author=author)
    assert post.content == "hello"
    assert post.author is author


def test_read_requires_an_open_session() -> None:
    try:
        PostSearch(_ClosedSession()).read(limit=1)  # type: ignore[arg-type]
    except BrowserLifecycleError as exc:
        assert "context manager" in str(exc)
    else:
        raise AssertionError("expected BrowserLifecycleError")


def test_fetch_returns_empty_for_non_positive_limit() -> None:
    assert PostSearch(_OpenSession()).fetch(limit=0) == []  # type: ignore[arg-type]
    assert PostSearch(_OpenSession()).read(limit=0) == []  # type: ignore[arg-type]


def test_posts_package_does_not_import_jobs() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "linkedin_search_posts"
    imports = []
    for path in root.rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                imports.append(stripped)
    joined = "\n".join(imports)
    assert "linkedin_search_jobs" not in joined
    assert "linkedin_client" not in joined
