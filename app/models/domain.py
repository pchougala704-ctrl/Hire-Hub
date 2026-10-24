from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Company:
    name: str
    id: str = ""
    description: str = ""
    location: str = ""
    website: str = ""
    verified: bool = False


@dataclass
class Application:
    candidate_id: str
    job_id: str
    status: str = "APPLIED"
    id: str = ""
    recruiter_id: str = ""
    applied_at: datetime | None = None
    recruiter_notes: str = ""
    interview_id: str = ""


@dataclass
class Interview:
    application_id: str
    candidate_id: str
    recruiter_id: str
    date: str
    time: str
    type: str = "ONLINE"
    status: str = "SCHEDULED"
    id: str = ""
    meeting_link: str = ""
    feedback: str = ""


@dataclass
class Resume:
    user_id: str
    original_name: str
    stored_name: str
    mime_type: str
    size: int
    id: str = ""
    created_at: datetime | None = None


@dataclass
class Notification:
    user_id: str
    message: str
    id: str = ""
    read: bool = False
    created_at: datetime | None = None
    metadata: dict = field(default_factory=dict)
