import pytest

from app.exceptions import ValidationError
from app.services.application_service import ApplicationService
from app.services.job_service import JobService


def test_job_number_parser_rejects_negative_values():
    with pytest.raises(ValidationError):
        JobService._optional_int("-1")


def test_job_keyword_search_includes_skills_and_applies_selected_filters(monkeypatch):
    captured = {}

    class FakeJobRepository:
        def __init__(self, db):
            pass

        def search(self, query, page, per_page):
            captured["query"] = query
            return [], 0

    monkeypatch.setattr("app.services.job_service.JobRepository", FakeJobRepository)
    JobService(None).search({
        "keyword": "full stack developer",
        "location": "city",
        "work_mode": "REMOTE",
        "employment_type": "INTERNSHIP",
    })

    query = captured["query"]
    keyword_conditions = query["$and"][0]["$or"]
    assert {"skills": {"$regex": "full\\ stack\\ developer", "$options": "i"}} in keyword_conditions
    assert query["location"] == {"$regex": "city", "$options": "i"}
    assert query["work_mode"] == "REMOTE"
    assert query["employment_type"] == "INTERNSHIP"


def test_terminal_application_statuses_cannot_transition():
    assert ApplicationService.TRANSITIONS["SELECTED"] == set()
    assert ApplicationService.TRANSITIONS["REJECTED"] == set()
