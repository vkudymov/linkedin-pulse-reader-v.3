from linkedin_client.parsing.author_extract import _clean_author_name, _looks_like_author_name


def test_clean_author_name_strips_connection_degree() -> None:
    assert _clean_author_name("Jane Doe • 1st") == "Jane Doe"


def test_looks_like_author_name_rejects_urls() -> None:
    assert _looks_like_author_name("https://linkedin.com/in/jane") is False
    assert _looks_like_author_name("Jane Doe") is True
