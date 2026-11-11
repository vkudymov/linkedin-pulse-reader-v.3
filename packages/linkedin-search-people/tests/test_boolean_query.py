from linkedin_search_people.navigation.boolean_query import normalize_boolean_query


def test_uppercases_operators_outside_quotes() -> None:
    r = normalize_boolean_query('маркетолог and B2B or "and more"')
    assert r.ok
    assert "AND" in r.query
    assert "OR" in r.query
    assert '"and more"' in r.query


def test_smart_quotes_become_straight() -> None:
    r = normalize_boolean_query("«product manager»")
    assert r.ok
    assert '"product manager"' in r.query


def test_plus_minus_warning() -> None:
    r = normalize_boolean_query("ABAP +HANA -junior")
    assert any("AND / NOT" in w for w in r.warnings)


def test_unbalanced_quotes() -> None:
    r = normalize_boolean_query('"product manager')
    assert not r.ok
    assert "unbalanced quotes" in r.errors


def test_cannot_start_with_and() -> None:
    r = normalize_boolean_query("AND ABAP")
    assert "query cannot start with AND/OR" in r.errors
