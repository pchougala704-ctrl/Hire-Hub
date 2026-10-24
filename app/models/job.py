from dataclasses import dataclass, field


@dataclass
class Job:
    title: str
    description: str
    recruiter_id: str
    company_id: str = ""
    skills: list[str] = field(default_factory=list)
    location: str = ""
    work_mode: str = "ONSITE"
    employment_type: str = "FULL_TIME"
    status: str = "OPEN"
    salary_min: int | None = None
    salary_max: int | None = None
