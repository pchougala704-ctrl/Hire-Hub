import re
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash

from app.exceptions import UserNotFoundError, ValidationError
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.models.user import User


class AdminService:
    def __init__(self, db):
        self.db = db

    def create_admin(self, name, email, password):
        name = str(name).strip()
        email = User.normalize_email(str(email))
        password = str(password)
        if len(name) < 2:
            raise ValidationError("Name must be at least 2 characters.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValidationError("Enter a valid email address.")
        if len(password) < 12:
            raise ValidationError("Administrator passwords must be at least 12 characters.")
        self.db["users"].create_index("email", unique=True)
        if self.db["users"].find_one({"email": email}):
            raise ValidationError("An account with that email already exists.")
        now = datetime.now(timezone.utc)
        try:
            user_id = self.db["users"].insert_one({
                "name": name,
                "email": email,
                "phone": "",
                "password_hash": generate_password_hash(password),
                "role": "ADMIN",
                "active": True,
                "created_at": now,
                "updated_at": now,
            }).inserted_id
        except DuplicateKeyError as exc:
            raise ValidationError("An account with that email already exists.") from exc
        AuditService(self.db).record(user_id, "ADMIN_ACCOUNT_CREATED", "user", user_id)
        return self.db["users"].find_one({"_id": user_id})

    def list_users(self, role=None, limit=200):
        query = {"role": role} if role else {}
        return list(
            self.db["users"].find(query, {"password_hash": 0})
            .sort("created_at", -1).limit(max(1, min(limit, 500)))
        )

    def set_user_active(self, user_id, active, actor=None):
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean.")
        oid = AuthService.object_id(user_id)
        target = self.db["users"].find_one({"_id": oid})
        if not target:
            raise UserNotFoundError("User not found.")
        if target.get("role") == "ADMIN" and actor and str(actor["_id"]) == str(oid) and not active:
            raise ValidationError("You cannot deactivate your own administrator account.")
        if target.get("role") == "ADMIN" and not active:
            active_admins = self.db["users"].count_documents({"role": "ADMIN", "active": {"$ne": False}})
            if active_admins <= 1:
                raise ValidationError("The last active administrator cannot be deactivated.")
        result = self.db["users"].update_one({"_id": oid}, {"$set": {"active": active}})
        if not result.matched_count:
            raise UserNotFoundError("User not found.")
        return oid

    def list_jobs(self, status=None, limit=200):
        query = {"status": status} if status else {}
        return list(
            self.db["jobs"].find(query).sort("created_at", -1)
            .limit(max(1, min(limit, 500)))
        )

    def list_applications(self, status=None, limit=200):
        query = {"status": status} if status else {}
        return list(
            self.db["applications"].find(query).sort("applied_at", -1)
            .limit(max(1, min(limit, 500)))
        )

    def dashboard_stats(self):
        stats = {
            "users": self.db["users"].count_documents({}),
            "candidates": self.db["users"].count_documents({"role": "CANDIDATE"}),
            "recruiters": self.db["users"].count_documents({"role": "RECRUITER"}),
            "companies": self.db["companies"].count_documents({}),
            "jobs": self.db["jobs"].count_documents({}),
            "open_jobs": self.db["jobs"].count_documents({"status": "OPEN"}),
            "applications": self.db["applications"].count_documents({}),
            "interviews": self.db["interviews"].count_documents({}),
            "selections": self.db["applications"].count_documents({"status": "SELECTED"}),
        }
        stats["applications_by_status"] = list(self.db["applications"].aggregate([
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]))
        return stats

    def list_companies(self, limit=200):
        return list(self.db["companies"].find().sort("created_at", -1).limit(limit))

    def set_company_verified(self, company_id, verified):
        if not isinstance(verified, bool):
            raise ValidationError("verified must be a boolean.")
        oid = AuthService.object_id(company_id)
        result = self.db["companies"].update_one({"_id": oid}, {"$set": {"verified": verified}})
        if not result.matched_count:
            raise ValidationError("Company not found.")
        return oid

    def audit_logs(self, limit=200):
        return list(
            self.db["audit_logs"].find().sort("timestamp", -1)
            .limit(max(1, min(limit, 500)))
        )
