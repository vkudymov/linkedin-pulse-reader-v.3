from linkedin_client.parsing.post_parser import parse_compact_number


def test_parse_compact_number_plain_int() -> None:
    assert parse_compact_number("123") == 123


def test_parse_compact_number_commas() -> None:
    assert parse_compact_number("1,234") == 1234


def test_parse_compact_number_compact_suffixes() -> None:
    assert parse_compact_number("1.2K") == 1200
    assert parse_compact_number("2M") == 2_000_000
    assert parse_compact_number("3B") == 3_000_000_000


def test_parse_compact_number_empty_or_invalid() -> None:
    assert parse_compact_number("") is None
    assert parse_compact_number("n/a") is None

