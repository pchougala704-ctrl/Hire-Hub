from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from app.exceptions import (
    ApplicationNotFoundError, DuplicateApplicationError, InvalidApplicationStatusError,
    JobClosedError, UnauthorizedError,
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService


class ApplicationService:
    TRANSITIONS = {
        "APPLIED": {"UNDER_REVIEW", "SHORTLISTED", "REJECTED", "WITHDRAWN"},
        "UNDER_REVIEW": {"SHORTLISTED", "REJECTED", "WITHDRAWN"},
        "SHORTLISTED": {"INTERVIEW_SCHEDULED", "SELECTED", "REJECTED", "WITHDRAWN"},
        "INTERVIEW_SCHEDULED": {"SELECTED", "REJECTED", "WITHDRAWN"},
        "SELECTED": set(), "REJECTED": set(), "WITHDRAWN": set(),
    }

    def __init__(self, db):
        self.db = db
        self.applications = db["applications"]
        self.audit = AuditService(db)

    def apply(self, job_id, candidate):
        oid = AuthService.object_id(job_id)
        job = self.db["jobs"].find_one({"_id": oid})
        if not job:
            from app.exceptions import JobNotFoundError
            raise JobNotFoundError("Job not found.")
        if job.get("status") != "OPEN":
            raise JobClosedError("This job is not accepting applications.")
        if job.get("deadline") and job["deadline"] < datetime.now(timezone.utc).date().isoformat():
            raise JobClosedError("The application deadline has passed.")
        candidate_id = str(candidate["_id"])
        if self.applications.find_one({"candidate_id": candidate_id, "job_id": str(oid)}):
            raise DuplicateApplicationError("You have already applied for this job.")
        now = datetime.now(timezone.utc)
        try:
            application_id = self.applications.insert_one({
                "candidate_id": candidate_id,
                "job_id": str(oid),
                "recruiter_id": str(job["recruiter_id"]),
                "status": "APPLIED",
                "applied_at": now,
                "updated_at": now,
                "recruiter_notes": "",
            }).inserted_id
        except DuplicateKeyError as exc:
            raise DuplicateApplicationError("You have already applied for this job.") from exc
        self.db["notifications"].insert_one({
            "user_id": str(job["recruiter_id"]),
            "message": "A candidate applied to one of your jobs.",
            "read": False,
            "created_at": now,
        })
        self.audit.record(candidate["_id"], "APPLICATION_SUBMITTED", "application", application_id)
        return application_id

    def list_for_user(self, user, limit=100):
        if user["role"] == "CANDIDATE":
            query = {"candidate_id": str(user["_id"])}
        elif user["role"] == "RECRUITER":
            query = {"recruiter_id": str(user["_id"])}
        else:
            query = {}
        return list(self.applications.find(query).sort("applied_at", -1).limit(limit))

    def list_with_jobs(self, user, limit=100):
        items = self.list_for_user(user, limit)
        for item in items:
            job_id = item.get("job_id", "")
            if ObjectId.is_valid(job_id):
                item["job"] = self.db["jobs"].find_one({"_id": ObjectId(job_id)})
        return items

    def get_for_user(self, application_id, user):
        oid = AuthService.object_id(application_id)
        application = self.applications.find_one({"_id": oid})
        if not application:
            raise ApplicationNotFoundError("Application not found.")
        if user["role"] == "CANDIDATE" and application["candidate_id"] != str(user["_id"]):
            raise UnauthorizedError("You cannot view this application.")
        if user["role"] == "RECRUITER" and application["recruiter_id"] != str(user["_id"]):
            raise UnauthorizedError("You cannot view this application.")
        return application

    def update_status(self, application_id, status, actor):
        status = str(status).upper()
        oid = AuthService.object_id(application_id)
        application = self.applications.find_one({"_id": oid})
        if not application:
            raise ApplicationNotFoundError("Application not found.")
        allowed = actor["role"] == "ADMIN" or (
            actor["role"] == "RECRUITER" and application["recruiter_id"] == str(actor["_id"])
        )
        candidate_withdrawing = (
            actor["role"] == "CANDIDATE" and application["candidate_id"] == str(actor["_id"])
            and status == "WITHDRAWN"
        )
        if not allowed and not candidate_withdrawing:
            raise UnauthorizedError("You cannot update this application.")
        if actor["role"] == "RECRUITER" and status == "WITHDRAWN":
            raise UnauthorizedError("Only the candidate can withdraw an application.")
        if status not in self.TRANSITIONS.get(application["status"], set()):
            raise InvalidApplicationStatusError(f"Cannot change {application['status']} to {status}.")
        self.applications.update_one({"_id": oid}, {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}})
        self.audit.record(actor["_id"], f"APPLICATION_{status}", "application", oid)
        if status in {"SHORTLISTED", "REJECTED", "SELECTED"}:
            self.db["notifications"].insert_one({
                "user_id": application["candidate_id"],
                "message": f"Your application status changed to {status.replace('_', ' ').lower()}.",
                "read": False,
                "created_at": datetime.now(timezone.utc),
            })
        return self.applications.find_one({"_id": oid})
