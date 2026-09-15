from linkedin_client.navigation.job_search_url import (
    build_jobs_search_query,
    compose_job_keywords,
    resolve_job_filters,
)


def test_defaults_apply_when_filters_empty() -> None:
    resolved = resolve_job_filters({})
    assert resolved["date_posted"] == "week"
    assert resolved["employment"] == "full_time"


def test_query_maps_linkedin_params() -> None:
    q = build_jobs_search_query(
        keywords="ABAP Developer",
        location="Europe",
        filters={
            "date_posted": "day",
            "remote": True,
            "easy_apply": True,
            "experience": "mid_senior",
            "employment": "contract",
            "company": "1441",
        },
    )
    assert q["keywords"] == "ABAP Developer"
    assert q["location"] == "Europe"
    assert q["f_TPR"] == "r86400"
    assert q["f_WT"] == "2"
    assert q["f_AL"] == "true"
    assert q["f_E"] == "4"
    assert q["f_JT"] == "C"
    assert q["f_C"] == "1441"


def test_company_name_appended_once() -> None:
    keywords = compose_job_keywords("ABAP Developer", {"company": "SAP"})
    assert keywords.endswith("SAP")
    again = compose_job_keywords("ABAP SAP", {"company": "SAP"})
    assert again.count("SAP") == 1
