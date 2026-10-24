from datetime import datetime, timezone

from app.exceptions import ApplicationNotFoundError, UnauthorizedError, ValidationError
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService


class InterviewService:
    TYPES = {"ONLINE", "PHONE", "IN_PERSON"}
    STATUSES = {"SCHEDULED", "COMPLETED", "CANCELLED"}

    def __init__(self, db):
        self.db = db

    def list_for_user(self, user, limit=100):
        if user["role"] == "CANDIDATE":
            query = {"candidate_id": str(user["_id"])}
        elif user["role"] == "RECRUITER":
            query = {"recruiter_id": str(user["_id"])}
        else:
            query = {}
        return list(self.db["interviews"].find(query).sort("date", 1).limit(limit))

    def schedule(self, application_id, values, recruiter):
        application_oid = AuthService.object_id(application_id)
        application = self.db["applications"].find_one({"_id": application_oid})
        if not application:
            raise ApplicationNotFoundError("Application not found.")
        if application["recruiter_id"] != str(recruiter["_id"]):
            raise UnauthorizedError("You cannot schedule an interview for this application.")
        if application["status"] != "SHORTLISTED":
            raise ValidationError("Shortlist the candidate before scheduling an interview.")
        interview_type = str(values.get("type", "ONLINE")).upper()
        if interview_type not in self.TYPES:
            raise ValidationError("Invalid interview type.")
        date_value = str(values.get("date", ""))
        time_value = str(values.get("time", ""))
        try:
            scheduled_at = datetime.strptime(
                f"{date_value} {time_value}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValidationError("Enter a valid interview date and time.") from exc
        now = datetime.now(timezone.utc)
        if scheduled_at <= now:
            raise ValidationError("Interview must be scheduled for a future date and time.")
        interview_id = self.db["interviews"].insert_one({
            "application_id": str(application_oid),
            "candidate_id": application["candidate_id"],
            "recruiter_id": str(recruiter["_id"]),
            "date": date_value,
            "time": time_value,
            "type": interview_type,
            "meeting_link": str(values.get("meeting_link", "")).strip(),
            "status": "SCHEDULED",
            "feedback": "",
            "created_at": now,
            "updated_at": now,
        }).inserted_id
        self.db["applications"].update_one({"_id": application_oid}, {"$set": {
            "status": "INTERVIEW_SCHEDULED",
            "interview_id": str(interview_id),
            "updated_at": now,
        }})
        self.db["notifications"].insert_one({
            "user_id": application["candidate_id"],
            "message": "An interview has been scheduled.",
            "read": False,
            "created_at": now,
        })
        AuditService(self.db).record(recruiter["_id"], "INTERVIEW_SCHEDULED", "interview", interview_id)
        return self.db["interviews"].find_one({"_id": interview_id})

    def update(self, interview_id, values, actor):
        oid = AuthService.object_id(interview_id)
        interview = self.db["interviews"].find_one({"_id": oid})
        if not interview:
            raise ValidationError("Interview not found.")
        if actor["role"] not in {"ADMIN", "RECRUITER"} or (
            actor["role"] == "RECRUITER" and interview["recruiter_id"] != str(actor["_id"])
        ):
            raise UnauthorizedError("You cannot update this interview.")
        updates = {}
        if "status" in values:
            status = str(values["status"]).upper()
            if status not in self.STATUSES:
                raise ValidationError("Invalid interview status.")
            updates["status"] = status
        if "feedback" in values:
            updates["feedback"] = str(values["feedback"]).strip()
        for field, format_string in (("date", "%Y-%m-%d"), ("time", "%H:%M")):
            if field in values:
                value = str(values[field])
                try:
                    datetime.strptime(value, format_string)
                except ValueError as exc:
                    raise ValidationError(f"Enter a valid interview {field}.") from exc
                updates[field] = value
        if not updates:
            raise ValidationError("Provide an interview status, date, time, or feedback.")
        updates["updated_at"] = datetime.now(timezone.utc)
        self.db["interviews"].update_one({"_id": oid}, {"$set": updates})
        if updates.get("status") == "CANCELLED":
            self.db["applications"].update_one(
                {"_id": AuthService.object_id(interview["application_id"]), "status": "INTERVIEW_SCHEDULED"},
                {"$set": {"status": "SHORTLISTED", "updated_at": datetime.now(timezone.utc)}},
            )
            self.db["notifications"].insert_one({
                "user_id": interview["candidate_id"],
                "message": "Your interview has been cancelled.",
                "read": False,
                "created_at": datetime.now(timezone.utc),
            })
        AuditService(self.db).record(actor["_id"], f"INTERVIEW_{updates.get('status', 'UPDATED')}", "interview", oid)
        return self.db["interviews"].find_one({"_id": oid})
