from job_search.dedupe import compute_source_key, extract_linkedin_job_id, normalize_job_url


def test_extract_job_id() -> None:
    assert extract_linkedin_job_id("https://www.linkedin.com/jobs/view/1234567890/") == "1234567890"


def test_normalize_job_url_strips_query() -> None:
    assert (
        normalize_job_url("https://www.linkedin.com/jobs/view/123/?foo=1#bar")
        == "https://www.linkedin.com/jobs/view/123"
    )


def test_compute_source_key_prefers_job_id() -> None:
    assert (
        compute_source_key(job_url="https://www.linkedin.com/jobs/view/999/", linkedin_job_id="123")
        == "job:123"
    )


def test_compute_source_key_from_url() -> None:
    assert compute_source_key(job_url="https://www.linkedin.com/jobs/view/999/") == "job:999"

