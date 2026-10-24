import pytest

from app.exceptions import ValidationError
from app.services.application_service import ApplicationService
from app.services.job_service import JobService


def test_job_number_parser_rejects_negative_values():
    with pytest.raises(ValidationError):
        JobService._optional_int("-1")


def test_terminal_application_statuses_cannot_transition():
    assert ApplicationService.TRANSITIONS["SELECTED"] == set()
    assert ApplicationService.TRANSITIONS["REJECTED"] == set()
