from linkedin_client.parsing.job_insights import classify_job_insights, normalize_insight_key


def test_classifies_russian_pills() -> None:
    r = classify_job_insights(["Работа в офисе", "Полный рабочий день"])
    assert r.workplace_type == "on_site"
    assert r.employment_type == "full_time"


def test_classifies_english_pills() -> None:
    r = classify_job_insights(["Hybrid", "Part-time"])
    assert r.workplace_type == "hybrid"
    assert r.employment_type == "part_time"


def test_classifies_from_location_blob() -> None:
    r = classify_job_insights([], location="Warsaw, Poland · On-site · 1 week ago")
    assert r.workplace_type == "on_site"
    assert r.employment_type is None


def test_classifies_employment_from_description_criteria() -> None:
    r = classify_job_insights(
        [],
        description="About the job\nWe build products.\nEmployment type\nFull-time\nJob function\nEngineering",
    )
    assert r.employment_type == "full_time"


def test_normalize_accepts_keys_and_labels() -> None:
    assert normalize_insight_key("remote") == "remote"
    assert normalize_insight_key("Удалённо") == "remote"
    assert normalize_insight_key("something else") is None
