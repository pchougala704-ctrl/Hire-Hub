from datetime import datetime, timezone
from datetime import date
import re

from app.exceptions import JobNotFoundError, UnauthorizedError, ValidationError
from app.repositories.job_repository import JobRepository
from app.services.auth_service import AuthService


class JobService:
    def __init__(self, db):
        self.db = db
        self.jobs = JobRepository(db)

    def search(self, filters, page=1, per_page=12):
        query = {"status": "OPEN"}
        query["$or"] = [
            {"deadline": {"$exists": False}},
            {"deadline": ""},
            {"deadline": {"$gte": date.today().isoformat()}},
        ]
        for key in ("location", "work_mode", "employment_type", "company_id"):
            value = filters.get(key)
            if value:
                query[key] = {"$regex": re.escape(str(value)), "$options": "i"} if key == "location" else str(value)
        if filters.get("keyword"):
            query["$and"] = [
                {"$or": [
                {"title": {"$regex": re.escape(str(filters["keyword"])), "$options": "i"}},
                {"description": {"$regex": re.escape(str(filters["keyword"])), "$options": "i"}},
                ]},
                {"$or": query.pop("$or")},
            ]
        if filters.get("skill"):
            query["skills"] = {"$regex": re.escape(str(filters["skill"])), "$options": "i"}
        for field in ("salary_min", "experience_min"):
            value = filters.get(field)
            if value is not None:
                try:
                    numeric_value = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(f"{field} must be a number.") from exc
                if field == "salary_min":
                    query["salary_max"] = {"$gte": numeric_value}
                else:
                    query["experience_max"] = {"$gte": numeric_value}
        try:
            page = max(1, min(int(page), 100000))
            per_page = max(1, min(int(per_page), 50))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Page and page size must be whole numbers.") from exc
        return self.jobs.search(query, page, per_page)

    def get(self, job_id):
        oid = AuthService.object_id(job_id)
        job = self.jobs.find_by_id(oid)
        if not job:
            raise JobNotFoundError("Job not found.")
        return job

    def for_recruiter(self, recruiter, limit=100):
        return list(
            self.jobs.collection.find({"recruiter_id": str(recruiter["_id"])}).sort("created_at", -1).limit(limit)
        )

    def create(self, values, recruiter):
        title = str(values.get("title", "")).strip()
        description = str(values.get("description", "")).strip()
        if not title or not description:
            raise ValidationError("Job title and description are required.")
        skills = values.get("skills", [])
        if isinstance(skills, str):
            skills = [item.strip() for item in skills.split(",") if item.strip()]
        if not isinstance(skills, list):
            raise ValidationError("Skills must be a list or comma-separated text.")
        skills = [str(skill).strip() for skill in skills if str(skill).strip()]
        work_mode = str(values.get("work_mode", "ONSITE")).upper()
        employment_type = str(values.get("employment_type", "FULL_TIME")).upper()
        if work_mode not in {"REMOTE", "HYBRID", "ONSITE"}:
            raise ValidationError("Invalid work mode.")
        if employment_type not in {"FULL_TIME", "PART_TIME", "INTERNSHIP", "CONTRACT"}:
            raise ValidationError("Invalid employment type.")
        now = datetime.now(timezone.utc)
        document = {
            "title": title,
            "description": description,
            "skills": skills,
            "location": str(values.get("location", "")).strip(),
            "work_mode": work_mode,
            "employment_type": employment_type,
            "recruiter_id": str(recruiter["_id"]),
            "company_id": recruiter.get("company_id", ""),
            "salary_min": self._optional_int(values.get("salary_min")),
            "salary_max": self._optional_int(values.get("salary_max")),
            "experience_min": self._optional_int(values.get("experience_min")),
            "experience_max": self._optional_int(values.get("experience_max")),
            "deadline": str(values.get("deadline", "")),
            "status": "OPEN",
            "created_at": now,
            "updated_at": now,
        }
        if document["salary_min"] and document["salary_max"] and document["salary_min"] > document["salary_max"]:
            raise ValidationError("Minimum salary cannot exceed maximum salary.")
        if document["experience_min"] is not None and document["experience_max"] is not None and document["experience_min"] > document["experience_max"]:
            raise ValidationError("Minimum experience cannot exceed maximum experience.")
        if document["deadline"]:
            try:
                datetime.strptime(document["deadline"], "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError("Deadline must be a valid date.") from exc
        return self.jobs.create(document)

    def update(self, job_id, values, actor):
        oid = AuthService.object_id(job_id)
        job = self.jobs.find_by_id(oid)
        if not job:
            raise JobNotFoundError("Job not found.")
        if actor["role"] != "ADMIN" and str(job["recruiter_id"]) != str(actor["_id"]):
            raise UnauthorizedError("You cannot manage this job.")
        allowed = {
            "title", "description", "skills", "location", "work_mode",
            "employment_type", "salary_min", "salary_max", "experience_min",
            "experience_max", "deadline",
        }
        updates = {key: values[key] for key in allowed if key in values}
        for field in ("title", "description", "location"):
            if field in updates:
                updates[field] = str(updates[field]).strip()
                if field in {"title", "description"} and not updates[field]:
                    raise ValidationError(f"{field.title()} cannot be empty.")
        if "skills" in updates:
            skills = updates["skills"]
            if isinstance(skills, str):
                skills = skills.split(",")
            if not isinstance(skills, list):
                raise ValidationError("Skills must be a list or comma-separated text.")
            updates["skills"] = [str(skill).strip() for skill in skills if str(skill).strip()]
        if "work_mode" in updates:
            updates["work_mode"] = str(updates["work_mode"]).upper()
            if updates["work_mode"] not in {"REMOTE", "HYBRID", "ONSITE"}:
                raise ValidationError("Invalid work mode.")
        if "employment_type" in updates:
            updates["employment_type"] = str(updates["employment_type"]).upper()
            if updates["employment_type"] not in {"FULL_TIME", "PART_TIME", "INTERNSHIP", "CONTRACT"}:
                raise ValidationError("Invalid employment type.")
        for field in ("salary_min", "salary_max", "experience_min", "experience_max"):
            if field in updates:
                updates[field] = self._optional_int(updates[field])
        if updates.get("deadline"):
            try:
                datetime.strptime(str(updates["deadline"]), "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError("Deadline must be a valid date.") from exc
        salary_min = updates.get("salary_min", job.get("salary_min"))
        salary_max = updates.get("salary_max", job.get("salary_max"))
        experience_min = updates.get("experience_min", job.get("experience_min"))
        experience_max = updates.get("experience_max", job.get("experience_max"))
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise ValidationError("Minimum salary cannot exceed maximum salary.")
        if experience_min is not None and experience_max is not None and experience_min > experience_max:
            raise ValidationError("Minimum experience cannot exceed maximum experience.")
        updates["updated_at"] = datetime.now(timezone.utc)
        self.jobs.collection.update_one({"_id": oid}, {"$set": updates})
        return self.jobs.find_by_id(oid)

    def close(self, job_id, actor):
        oid = AuthService.object_id(job_id)
        job = self.jobs.find_by_id(oid)
        if not job:
            raise JobNotFoundError("Job not found.")
        if actor["role"] != "ADMIN" and str(job["recruiter_id"]) != str(actor["_id"]):
            raise UnauthorizedError("You cannot manage this job.")
        self.jobs.collection.update_one({"_id": oid}, {"$set": {"status": "CLOSED", "updated_at": datetime.now(timezone.utc)}})

    def moderate(self, job_id, status):
        oid = AuthService.object_id(job_id)
        status = str(status).upper()
        if status not in {"OPEN", "CLOSED", "EXPIRED"}:
            raise ValidationError("Invalid job status.")
        result = self.jobs.collection.update_one(
            {"_id": oid},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
        )
        if not result.matched_count:
            raise JobNotFoundError("Job not found.")
        return oid

    @staticmethod
    def _optional_int(value):
        if value in (None, ""):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Salary and experience values must be whole numbers.") from exc
        if number < 0:
            raise ValidationError("Salary and experience values cannot be negative.")
        return number
