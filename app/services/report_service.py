import re
from datetime import datetime, time, timedelta, timezone

from app.exceptions import ValidationError


class ReportService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _date_range(filters):
        query = {}
        start_value = filters.get("date_from")
        end_value = filters.get("date_to")
        try:
            if start_value:
                start_date = datetime.strptime(start_value, "%Y-%m-%d").date()
                query["$gte"] = datetime.combine(start_date, time.min, timezone.utc)
            if end_value:
                end_date = datetime.strptime(end_value, "%Y-%m-%d").date() + timedelta(days=1)
                query["$lt"] = datetime.combine(end_date, time.min, timezone.utc)
        except ValueError as exc:
            raise ValidationError("Report dates must use YYYY-MM-DD format.") from exc
        if start_value and end_value and query["$gte"] >= query["$lt"]:
            raise ValidationError("Report start date must not be after its end date.")
        return query

    def applications(self, filters):
        query = {}
        if filters.get("status"):
            query["status"] = filters["status"].upper()
        date_range = self._date_range(filters)
        if date_range:
            query["applied_at"] = date_range
        if filters.get("company_id") or filters.get("location"):
            job_query = {}
            if filters.get("company_id"):
                job_query["company_id"] = filters["company_id"]
            if filters.get("location"):
                job_query["location"] = {"$regex": re.escape(filters["location"]), "$options": "i"}
            job_ids = [str(item["_id"]) for item in self.db["jobs"].find(job_query, {"_id": 1})]
            query["job_id"] = {"$in": job_ids}
        items = self.db["applications"].find(query).sort("applied_at", -1).limit(10000)
        return [
            [item["_id"], item.get("candidate_id"), item.get("job_id"), item.get("status"), item.get("applied_at")]
            for item in items
        ]

    def candidates(self, filters):
        query = {"role": "CANDIDATE"}
        date_range = self._date_range(filters)
        if date_range:
            query["created_at"] = date_range
        items = self.db["users"].find(query).sort("created_at", -1).limit(10000)
        rows = []
        for item in items:
            profile = self.db["candidates"].find_one({"user_email": item["email"]}) or {}
            rows.append([
                item["_id"], item.get("name"), item.get("email"),
                profile.get("location"), item.get("created_at"),
            ])
        return rows

    def jobs(self, filters):
        query = {}
        for field in ("company_id", "status"):
            if filters.get(field):
                query[field] = filters[field].upper() if field == "status" else filters[field]
        if filters.get("location"):
            query["location"] = {"$regex": re.escape(filters["location"]), "$options": "i"}
        date_range = self._date_range(filters)
        if date_range:
            query["created_at"] = date_range
        items = self.db["jobs"].find(query).sort("created_at", -1).limit(10000)
        return [
            [
                item["_id"], item.get("title"), item.get("company_id"), item.get("location"),
                item.get("work_mode"), item.get("employment_type"), item.get("status"),
                item.get("created_at"),
            ]
            for item in items
        ]

    def skills(self, filters):
        query = {"status": "OPEN"}
        if filters.get("company_id"):
            query["company_id"] = filters["company_id"]
        if filters.get("location"):
            query["location"] = {"$regex": re.escape(filters["location"]), "$options": "i"}
        rows = self.db["jobs"].aggregate([
            {"$match": query},
            {"$unwind": "$skills"},
            {"$group": {"_id": "$skills", "openings": {"$sum": 1}}},
            {"$sort": {"openings": -1, "_id": 1}},
            {"$limit": 1000},
        ])
        return [[item["_id"], item["openings"]] for item in rows]

    def recruitment(self):
        recruiters = self.db["users"].find({"role": "RECRUITER"}).limit(10000)
        return [
            [
                item["_id"], item.get("name"), item.get("email"),
                self.db["jobs"].count_documents({"recruiter_id": str(item["_id"])}),
                self.db["applications"].count_documents({"recruiter_id": str(item["_id"])}),
                self.db["applications"].count_documents({
                    "recruiter_id": str(item["_id"]), "status": "SELECTED",
                }),
            ]
            for item in recruiters
        ]
