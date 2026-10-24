from app.exceptions import UnauthorizedError, ValidationError


class AnalyticsService:
    def __init__(self, db):
        self.db = db

    def for_role(self, requested_role, user):
        role = requested_role.lower()
        if role != user["role"].lower() and user["role"] != "ADMIN":
            raise UnauthorizedError("You cannot view these analytics.")
        if role == "candidate":
            query = {"candidate_id": str(user["_id"])}
            return {
                "applications_by_status": list(self.db["applications"].aggregate([
                    {"$match": query},
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                ])),
                "total_applications": self.db["applications"].count_documents(query),
                "interviews": self.db["interviews"].count_documents(query),
                "selections": self.db["applications"].count_documents({**query, "status": "SELECTED"}),
            }
        if role == "recruiter":
            query = {"recruiter_id": str(user["_id"])}
            return {
                "jobs": self.db["jobs"].count_documents(query),
                "active_jobs": self.db["jobs"].count_documents({**query, "status": "OPEN"}),
                "applications": self.db["applications"].count_documents(query),
                "interviews": self.db["interviews"].count_documents(query),
                "selections": self.db["applications"].count_documents({**query, "status": "SELECTED"}),
                "applications_by_status": list(self.db["applications"].aggregate([
                    {"$match": query},
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                ])),
            }
        if role == "admin":
            return {
                "users": self.db["users"].count_documents({}),
                "candidates": self.db["users"].count_documents({"role": "CANDIDATE"}),
                "recruiters": self.db["users"].count_documents({"role": "RECRUITER"}),
                "jobs": self.db["jobs"].count_documents({}),
                "interviews": self.db["interviews"].count_documents({}),
                "applications_by_status": list(self.db["applications"].aggregate([
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                ])),
                "jobs_by_location": list(self.db["jobs"].aggregate([
                    {"$match": {"status": "OPEN"}},
                    {"$group": {"_id": "$location", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10},
                ])),
                "top_demanded_skills": list(self.db["jobs"].aggregate([
                    {"$match": {"status": "OPEN"}},
                    {"$unwind": "$skills"},
                    {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10},
                ])),
                "applications_by_job": list(self.db["applications"].aggregate([
                    {"$group": {"_id": "$job_id", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10},
                ])),
                "applications_by_company": list(self.db["applications"].aggregate([
                    {"$addFields": {
                        "job_object_id": {
                            "$convert": {
                                "input": "$job_id",
                                "to": "objectId",
                                "onError": None,
                                "onNull": None,
                            }
                        }
                    }},
                    {"$lookup": {
                        "from": "jobs",
                        "localField": "job_object_id",
                        "foreignField": "_id",
                        "as": "job",
                    }},
                    {"$unwind": "$job"},
                    {"$group": {"_id": "$job.company_id", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10},
                ])),
                "recruiter_statistics": list(self.db["users"].aggregate([
                    {"$match": {"role": "RECRUITER"}},
                    {"$addFields": {"recruiter_id": {"$toString": "$_id"}}},
                    {"$lookup": {
                        "from": "jobs",
                        "localField": "recruiter_id",
                        "foreignField": "recruiter_id",
                        "as": "jobs",
                    }},
                    {"$lookup": {
                        "from": "applications",
                        "localField": "recruiter_id",
                        "foreignField": "recruiter_id",
                        "as": "applications",
                    }},
                    {"$project": {
                        "name": 1,
                        "email": 1,
                        "jobs": {"$size": "$jobs"},
                        "applications": {"$size": "$applications"},
                    }},
                    {"$sort": {"applications": -1}},
                    {"$limit": 20},
                ])),
                "candidate_statistics": list(self.db["applications"].aggregate([
                    {"$group": {
                        "_id": "$candidate_id",
                        "applications": {"$sum": 1},
                        "selections": {
                            "$sum": {"$cond": [{"$eq": ["$status", "SELECTED"]}, 1, 0]}
                        },
                    }},
                    {"$sort": {"applications": -1}},
                    {"$limit": 20},
                ])),
                "monthly_registrations": list(self.db["users"].aggregate([
                    {"$match": {"created_at": {"$type": "date"}}},
                    {"$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
                        "count": {"$sum": 1},
                    }},
                    {"$sort": {"_id": 1}},
                ])),
                "monthly_applications": list(self.db["applications"].aggregate([
                    {"$match": {"applied_at": {"$type": "date"}}},
                    {"$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m", "date": "$applied_at"}},
                        "count": {"$sum": 1},
                    }},
                    {"$sort": {"_id": 1}},
                ])),
            }
        raise ValidationError("Unknown analytics role.")
