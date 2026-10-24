import re
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.exceptions import InvalidCredentialsError, UserAlreadyExistsError, ValidationError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db):
        self.users = UserRepository(db)
        self.db = db
        self.audit = AuditService(db)

    def register(self, values):
        name = str(values.get("name", "")).strip()
        email = User.normalize_email(str(values.get("email", "")))
        password = str(values.get("password", ""))
        role = str(values.get("role", "CANDIDATE")).upper()
        if role not in {"CANDIDATE", "RECRUITER"}:
            raise ValidationError("Public registration is limited to candidates and recruiters.")
        if len(name) < 2 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValidationError("Enter a name and a valid email address.")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        phone = str(values.get("phone", "")).strip()
        if phone and not re.fullmatch(r"[+()\d .-]{7,24}", phone):
            raise ValidationError("Enter a valid phone number.")
        if values.get("confirm_password") is None or password != values.get("confirm_password"):
            raise ValidationError("Passwords do not match.")
        if self.users.by_email(email):
            raise UserAlreadyExistsError("An account with this email already exists.")
        now = datetime.now(timezone.utc)
        user = {
            "name": name,
            "email": email,
            "phone": phone,
            "password_hash": generate_password_hash(password),
            "role": role,
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        company_name = ""
        if role == "RECRUITER":
            company_name = str(values.get("company_name", "")).strip()
            if not company_name:
                raise ValidationError("Company name is required for recruiter registration.")
            company_id = self.db["companies"].insert_one({
                "name": company_name,
                "verified": False,
                "created_at": now,
            }).inserted_id
            user["company_id"] = str(company_id)
        try:
            user_id = self.users.create(user)
        except DuplicateKeyError as exc:
            if role == "RECRUITER":
                self.db["companies"].delete_one({"_id": company_id})
            raise UserAlreadyExistsError("An account with this email already exists.") from exc
        if role == "RECRUITER":
            self.db["recruiters"].insert_one({"user_email": email, "company_id": str(company_id)})
        else:
            self.db["candidates"].insert_one({"user_email": email, "skills": [], "saved_jobs": []})
        self.audit.record(user_id, "USER_REGISTERED", "user", user_id, {"role": role})
        self.db["notifications"].insert_one({
            "user_id": str(user_id),
            "message": "Welcome to HireHub. Complete your profile to get better matches.",
            "read": False,
            "created_at": now,
        })
        return self.users.by_id(user_id)

    def login(self, email, password):
        user = self.users.by_email(User.normalize_email(str(email or "")))
        if not user or not user.get("active", True) or not check_password_hash(user["password_hash"], str(password or "")):
            raise InvalidCredentialsError("Email or password is incorrect.")
        self.audit.record(user["_id"], "USER_LOGIN", "user", user["_id"])
        return user

    @staticmethod
    def object_id(value):
        if not ObjectId.is_valid(str(value)):
            raise ValidationError("Invalid identifier.")
        return ObjectId(str(value))
