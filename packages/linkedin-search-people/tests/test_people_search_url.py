from linkedin_search_people.navigation.people_search_url import (
    build_people_search_query,
    compose_people_keywords,
    resolve_people_filters,
)


def test_defaults_empty() -> None:
    resolved = resolve_people_filters({})
    assert resolved["network"] == []
    assert resolved["profile_language"] == ""


def test_query_maps_facets() -> None:
    q = build_people_search_query(
        keywords="ABAP AND HANA",
        filters={
            "network": ["F", "S"],
            "locations": ["103644278"],
            "current_company": ["1441"],
            "past_company": ["urn:li:organization:1814"],
            "school": ["1503"],
            "industry": ["96"],
            "profile_language": "en",
        },
    )
    assert "ABAP AND HANA" in q["keywords"]
    assert q["network"] == '["F","S"]'
    assert q["geoUrn"] == '["103644278"]'
    assert q["currentCompany"] == '["1441"]'
    assert q["pastCompany"] == '["1814"]'
    assert q["schoolFilter"] == '["1503"]'
    assert q["industry"] == '["96"]'
    assert q["profileLanguage"] == '["en"]'


def test_company_name_appended_as_quoted_keyword() -> None:
    q = build_people_search_query(keywords="ABAP", filters={"current_company": ["SAP"]})
    assert '"SAP"' in q["keywords"]


def test_boolean_normalized() -> None:
    composed = compose_people_keywords('маркетолог and B2B', None)
    assert "AND" in composed
