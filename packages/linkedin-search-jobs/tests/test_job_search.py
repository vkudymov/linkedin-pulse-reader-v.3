from pathlib import Path

from linkedin_search_core.exceptions import BrowserLifecycleError
from linkedin_search_jobs import Job, JobSearch
from linkedin_search_jobs.loading.guest_jobs import parse_guest_jobs_html
from linkedin_search_jobs.navigation.job_search_url import build_jobs_search_url
from linkedin_search_jobs.parsing import job_parser as job_parser_mod


class _ClosedSession:
    _entered = False


class _OpenSession:
    _entered = True


def test_job_model_keeps_listing_fields() -> None:
    job = Job(job_id="1", title="ABAP Developer", company="SAP", location="Berlin")
    assert job.job_id == "1"
    assert job.title == "ABAP Developer"
    assert job.insights == ()


def test_fetch_requires_an_open_session() -> None:
    try:
        JobSearch(_ClosedSession()).fetch(keywords="ABAP")  # type: ignore[arg-type]
    except BrowserLifecycleError as exc:
        assert "context manager" in str(exc)
    else:
        raise AssertionError("expected BrowserLifecycleError")


def test_fetch_returns_empty_for_non_positive_limit() -> None:
    assert JobSearch(_OpenSession()).fetch(keywords="ABAP", limit=0) == []  # type: ignore[arg-type]


def test_search_url_includes_keywords() -> None:
    url = build_jobs_search_url(
        base_url="https://www.linkedin.com/jobs/search/",
        keywords="ABAP",
        location="Berlin",
        filters={},
    )
    assert "keywords=" in url
    assert "ABAP" in url
    assert "location=Berlin" in url


def test_clean_semantic_job_title() -> None:
    raw = (
        "Выбрано, «SAP ABAP S/4 Hana Architect - UK» (подтвержденная вакансия)\n"
        "SAP ABAP S/4 Hana Architect - UK"
    )
    assert job_parser_mod._clean_job_title(raw) == "SAP ABAP S/4 Hana Architect - UK"
    assert job_parser_mod._job_id_from_componentkey("job-card-component-ref-4405179449") == (
        "4405179449"
    )


def test_parse_guest_jobs_html_extracts_cards() -> None:
    html = """
    <div data-entity-urn="urn:li:jobPosting:111">
      <h3 class="base-search-card__title">ABAP Developer</h3>
      <h4 class="base-search-card__subtitle">SAP</h4>
      <span class="job-search-card__location">London, England</span>
    </div>
    """
    jobs = parse_guest_jobs_html(html)
    assert len(jobs) == 1
    assert jobs[0].job_id == "111"
    assert jobs[0].title == "ABAP Developer"
    assert jobs[0].company == "SAP"
    assert jobs[0].job_url == "https://www.linkedin.com/jobs/view/111"


def test_current_job_id_from_search_results_url() -> None:
    url = (
        "https://www.linkedin.com/jobs/search-results/"
        "?currentJobId=4405179449&keywords=ABAP"
    )
    assert job_parser_mod._job_id_from_page_url(url) == "4405179449"
    assert job_parser_mod._job_id_from_page_url("https://www.linkedin.com/jobs/search/") is None


def test_jobs_package_does_not_import_posts() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "linkedin_search_jobs"
    imports = []
    for path in root.rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                imports.append(stripped)
    joined = "\n".join(imports)
    assert "linkedin_search_posts" not in joined
    assert "linkedin_client" not in joined
