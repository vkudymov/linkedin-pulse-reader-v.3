import pytest

from job_search.analysis import parse_job_match_json


def test_parse_job_match_json_ok() -> None:
    r = parse_job_match_json(
        """
        {
          "match": true,
          "score": 87,
          "reason": "Strong fit",
          "matched_requirements": ["Prompt engineering", "Python"],
          "missing_requirements": ["5+ years"],
          "red_flags": []
        }
        """,
    )
    assert r.match is True
    assert r.score == 87
    assert r.reason == "Strong fit"
    assert "Prompt engineering" in r.matched_requirements


def test_parse_job_match_json_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        parse_job_match_json("[]")


def test_parse_job_match_json_requires_score_int() -> None:
    with pytest.raises(ValueError):
        parse_job_match_json(
            '{"match":true,"score":"87","reason":"x","matched_requirements":[],"missing_requirements":[],"red_flags":[]}',
        )

