from app.exceptions import ValidationError, UserNotFoundError
from app.services.auth_service import AuthService


class AdminService:
    def __init__(self, db):
        self.db = db

    def list_users(self, limit=200):
        return list(self.db["users"].find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit))

    def set_user_active(self, user_id, active):
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean.")
        oid = AuthService.object_id(user_id)
        result = self.db["users"].update_one({"_id": oid}, {"$set": {"active": active}})
        if not result.matched_count:
            raise UserNotFoundError("User not found.")
        return oid

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
        return list(self.db["audit_logs"].find().sort("timestamp", -1).limit(limit))
