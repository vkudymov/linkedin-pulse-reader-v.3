from pathlib import Path
import re

from linkedin_search_people.parsing.people_parser import (
    clean_headline,
    clean_person_name,
    extract_public_id,
    normalize_avatar_url,
    normalize_profile_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extract_public_id() -> None:
    assert extract_public_id("https://www.linkedin.com/in/jane-doe/") == "jane-doe"
    assert extract_public_id("/in/jane-doe?miniProfileUrn=x") == "jane-doe"
    assert extract_public_id("https://linkedin.com/jobs/view/1") is None


def test_normalize_profile_url() -> None:
    url = normalize_profile_url("/in/jane-doe?trk=people")
    assert url == "https://www.linkedin.com/in/jane-doe"


def test_clean_person_name_strips_degree_trailer() -> None:
    assert clean_person_name("Jane Doe • 3-й+ SAP") == "Jane Doe"
    assert clean_person_name("  Bob  ") == "Bob"


def test_clean_headline_strips_linkedin_noise() -> None:
    raw = (
        "Certified SAP ABAP | London, UK Установить контакт "
        "Текущая: ABAP RAP Specialist – SAP"
    )
    cleaned = clean_headline(raw, location="London, UK", name="Jane")
    assert cleaned is not None
    assert "Установить контакт" not in cleaned
    assert "Текущая:" not in cleaned


def test_normalize_avatar_url() -> None:
    real = "https://media.licdn.com/dms/image/v2/D4E03AQJane/profile-displayphoto-shrink_100_100/jane.jpg"
    assert normalize_avatar_url(real) == real
    assert normalize_avatar_url("https://static.licdn.com/aero-v1/sc/h/ghost-person") is None
    assert normalize_avatar_url("data:image/gif;base64,abc") is None
    assert normalize_avatar_url(None) is None


def test_person_card_fixture_fields() -> None:
    html = _read("person_card.html")
    href = re.search(r'href="([^"]*/in/[^"]+)"', html)
    assert href is not None
    assert extract_public_id(href.group(1)) == "jane-doe"
    assert normalize_profile_url(href.group(1)) == "https://www.linkedin.com/in/jane-doe"
    assert "Jane Doe" in html
    assert "SAP ABAP Developer at ACME" in html
    assert "Berlin, Germany" in html
    assert "2nd" in html
    assert "S/4HANA" in html
    assert "profile-displayphoto" in html


def test_profile_fixture_sections() -> None:
    html = _read("profile.html")
    assert "Jane Doe" in html
    assert "About" in html
    assert "ABAP developer with 8 years" in html
    assert "ABAP" in html and "CDS" in html and "HANA" in html
    assert "Experience" in html
    assert "Education" in html
    assert "TU Berlin" in html
    assert "profile-displayphoto-shrink_400_400" in html
