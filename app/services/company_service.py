from urllib.parse import urlparse

from bson import ObjectId

from app.exceptions import UnauthorizedError, ValidationError


class CompanyService:
    FIELDS = {"name", "description", "location", "website"}

    def __init__(self, db):
        self.db = db

    def get_for_recruiter(self, recruiter):
        company_id = recruiter.get("company_id", "")
        if not ObjectId.is_valid(company_id):
            return None
        return self.db["companies"].find_one({"_id": ObjectId(company_id)})

    def update_for_recruiter(self, values, recruiter):
        company = self.get_for_recruiter(recruiter)
        if not company:
            raise ValidationError("Company profile not found.")
        updates = {
            key: str(values[key]).strip()
            for key in self.FIELDS if key in values
        }
        if "name" in updates and not updates["name"]:
            raise ValidationError("Company name cannot be empty.")
        if "website" in updates and updates["website"]:
            parsed = urlparse(updates["website"])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValidationError("Enter a valid company website URL.")
        if not updates:
            raise ValidationError("Provide at least one company profile field.")
        self.db["companies"].update_one({"_id": company["_id"]}, {"$set": updates})
        return self.db["companies"].find_one({"_id": company["_id"]})
