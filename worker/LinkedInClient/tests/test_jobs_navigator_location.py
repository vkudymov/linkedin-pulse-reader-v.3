from linkedin_client.navigation.jobs import normalize_location_text


def test_normalize_location_text_strips_and_handles_empty() -> None:
    assert normalize_location_text(None) is None
    assert normalize_location_text("") is None
    assert normalize_location_text("   ") is None
    assert normalize_location_text(" Paris ") == "Paris"
