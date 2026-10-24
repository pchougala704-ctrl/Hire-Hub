import re

from bson import ObjectId

from app.exceptions import UnauthorizedError, UserNotFoundError, ValidationError
from app.services.auth_service import AuthService


class CandidateService:
    PROFILE_FIELDS = {
        "location", "skills", "education", "experience", "experience_years",
        "expected_salary", "notice_period", "preferred_work_mode",
    }

    def __init__(self, db):
        self.db = db

    def get_profile(self, user):
        return self.db["candidates"].find_one({"user_email": user["email"]}) or {}

    def update_web_profile(self, values, user):
        name = str(values.get("name", user["name"])).strip()
        phone = str(values.get("phone", "")).strip()
        if not name or (phone and not re.fullmatch(r"[+()\d .-]{7,24}", phone)):
            raise ValidationError("Enter a name and a valid phone number.")
        skills = [skill.strip() for skill in str(values.get("skills", "")).split(",") if skill.strip()]
        salary_value = str(values.get("expected_salary", "")).strip()
        experience_value = str(values.get("experience_years", "")).strip()
        try:
            expected_salary = int(salary_value) if salary_value else None
            experience_years = int(experience_value) if experience_value else None
        except ValueError as exc:
            raise ValidationError("Salary and experience must be whole numbers.") from exc
        if expected_salary is not None and expected_salary < 0:
            raise ValidationError("Expected salary cannot be negative.")
        if experience_years is not None and experience_years < 0:
            raise ValidationError("Experience cannot be negative.")
        preferred_work_mode = str(values.get("preferred_work_mode", "")).upper()
        if preferred_work_mode and preferred_work_mode not in {"REMOTE", "HYBRID", "ONSITE"}:
            raise ValidationError("Invalid preferred work mode.")
        self.db["users"].update_one({"_id": user["_id"]}, {"$set": {"name": name, "phone": phone}})
        self.db["candidates"].update_one({"user_email": user["email"]}, {"$set": {
            "location": str(values.get("location", "")).strip(),
            "skills": skills,
            "education": str(values.get("education", "")).strip(),
            "experience": str(values.get("experience", "")).strip(),
            "experience_years": experience_years,
            "expected_salary": expected_salary,
            "notice_period": str(values.get("notice_period", "")).strip(),
            "preferred_work_mode": preferred_work_mode,
        }}, upsert=True)
        return self.get_profile(user)

    def update_api_profile(self, values, user):
        if "skills" in values and not isinstance(values["skills"], list):
            raise ValidationError("Skills must be a list.")
        updates = {key: values[key] for key in self.PROFILE_FIELDS if key in values}
        for field in ("expected_salary", "experience_years"):
            if field in updates:
                try:
                    updates[field] = int(updates[field]) if updates[field] not in (None, "") else None
                except (TypeError, ValueError) as exc:
                    raise ValidationError("Salary and experience must be whole numbers.") from exc
                if updates[field] is not None and updates[field] < 0:
                    raise ValidationError(f"{field.replace('_', ' ').title()} cannot be negative.")
        if "preferred_work_mode" in updates:
            updates["preferred_work_mode"] = str(updates["preferred_work_mode"]).upper()
            if updates["preferred_work_mode"] not in {"", "REMOTE", "HYBRID", "ONSITE"}:
                raise ValidationError("Invalid preferred work mode.")
        if "skills" in updates:
            updates["skills"] = [str(skill).strip() for skill in updates["skills"] if str(skill).strip()]
        self.db["candidates"].update_one({"user_email": user["email"]}, {"$set": updates}, upsert=True)
        return self.get_profile(user)

    def toggle_saved_job(self, job_id, user):
        profile = self.get_profile(user)
        saved_jobs = profile.get("saved_jobs", [])
        if job_id in saved_jobs:
            saved_jobs.remove(job_id)
            saved = False
        else:
            saved_jobs.append(job_id)
            saved = True
        self.db["candidates"].update_one(
            {"user_email": user["email"]},
            {"$set": {"saved_jobs": saved_jobs}},
            upsert=True,
        )
        return saved

    def saved_jobs(self, user, limit=100):
        profile = self.get_profile(user)
        ids = [ObjectId(job_id) for job_id in profile.get("saved_jobs", []) if ObjectId.is_valid(job_id)]
        if not ids:
            return []
        return list(self.db["jobs"].find({"_id": {"$in": ids}}).sort("created_at", -1).limit(limit))

    def search(self, filters, limit=50):
        query = {}
        for field in ("skills", "location"):
            value = str(filters.get(field, "")).strip()
            if value:
                query[field] = {"$regex": re.escape(value), "$options": "i"}
        profiles = self.db["candidates"].find(query).limit(max(1, min(limit, 100)))
        results = []
        for profile in profiles:
            user = self.db["users"].find_one(
                {"email": profile["user_email"], "role": "CANDIDATE", "active": {"$ne": False}},
                {"password_hash": 0},
            )
            if user:
                results.append({"user": user, "profile": profile})
        return results

    def get_profile_for_viewer(self, candidate_id, viewer):
        oid = AuthService.object_id(candidate_id)
        candidate_user = self.db["users"].find_one({
            "_id": oid, "role": "CANDIDATE", "active": {"$ne": False},
        })
        if not candidate_user:
            raise UserNotFoundError("Candidate not found.")
        allowed = viewer["role"] == "ADMIN" or (
            viewer["role"] == "CANDIDATE" and viewer["_id"] == oid
        )
        if viewer["role"] == "RECRUITER":
            allowed = self.db["applications"].find_one({
                "candidate_id": str(oid), "recruiter_id": str(viewer["_id"]),
            }) is not None
        if not allowed:
            raise UnauthorizedError("You cannot view this candidate profile.")
        profile = self.get_profile(candidate_user)
        return {"user": candidate_user, "profile": profile}
