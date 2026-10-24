from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class User:
    name: str
    email: str
    role: str
    phone: str = ""
    id: str = ""
    active: bool = True

    COLLECTION: ClassVar[str] = "users"

    @property
    def display_name(self) -> str:
        return self.name.strip() or self.email

    @classmethod
    def from_document(cls, document: dict):
        model = {
            "CANDIDATE": Candidate,
            "RECRUITER": Recruiter,
            "ADMIN": Admin,
        }.get(document.get("role"), cls)
        return model(
            name=document.get("name", ""),
            email=document.get("email", ""),
            role=document.get("role", ""),
            phone=document.get("phone", ""),
            id=str(document.get("_id", "")),
            active=document.get("active", True),
        )

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()


@dataclass
class Candidate(User):
    skills: list[str] = field(default_factory=list)
    location: str = ""
    experience_years: int | None = None
    preferred_work_mode: str = ""


@dataclass
class Recruiter(User):
    company_id: str = ""


@dataclass
class Admin(User):
    pass
