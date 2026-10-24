from app.services.matching_service import MatchingService


def test_score_reports_matched_and_missing_skills():
    result = MatchingService.score(
        {"skills": ["Python", "SQL", "MongoDB"]},
        {"skills": ["Python", "SQL", "MongoDB", "AWS"], "location": "Bengaluru"},
    )
    assert result["score"] == 75
    assert result["matched_skills"] == ["mongodb", "python", "sql"]
    assert result["missing_skills"] == ["aws"]


def test_score_is_full_when_job_does_not_specify_skills():
    result = MatchingService.score({"skills": []}, {"skills": []})
    assert result["score"] == 100
