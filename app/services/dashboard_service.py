from app.services.recommendation_service import RecommendationService


class DashboardService:
    def __init__(self, db):
        self.db = db

    def for_user(self, user):
        data = {}
        if user["role"] == "CANDIDATE":
            application_query = {"candidate_id": str(user["_id"])}
            data["applications"] = list(
                self.db["applications"].find(application_query).sort("applied_at", -1).limit(10)
            )
            data["application_total"] = self.db["applications"].count_documents(application_query)
            data["shortlisted_total"] = self.db["applications"].count_documents(
                {**application_query, "status": "SHORTLISTED"}
            )
            data["interview_total"] = self.db["applications"].count_documents(
                {**application_query, "status": "INTERVIEW_SCHEDULED"}
            )
            data["selected_total"] = self.db["applications"].count_documents(
                {**application_query, "status": "SELECTED"}
            )
            profile = self.db["candidates"].find_one({"user_email": user["email"]}) or {}
            data["saved_total"] = len(profile.get("saved_jobs", []))
            fields = ("location", "skills", "education", "experience", "expected_salary", "notice_period")
            data["profile_completion"] = round(sum(bool(profile.get(field)) for field in fields) / len(fields) * 100)
            data["recommendations"] = [
                (item["match"], item["job"])
                for item in RecommendationService(self.db).for_candidate(user, 5)
            ]
            data["notifications"] = list(
                self.db["notifications"].find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(5)
            )
        elif user["role"] == "RECRUITER":
            query = {"recruiter_id": str(user["_id"])}
            data["jobs"] = list(self.db["jobs"].find(query).sort("created_at", -1).limit(10))
            data["applications"] = list(
                self.db["applications"].find(query).sort("applied_at", -1).limit(10)
            )
            data["jobs_total"] = self.db["jobs"].count_documents(query)
            data["active_jobs"] = self.db["jobs"].count_documents({**query, "status": "OPEN"})
            data["applications_total"] = self.db["applications"].count_documents(query)
            data["shortlisted_total"] = self.db["applications"].count_documents(
                {**query, "status": "SHORTLISTED"}
            )
            data["interviews_total"] = self.db["interviews"].count_documents(query)
            data["selections_total"] = self.db["applications"].count_documents(
                {**query, "status": "SELECTED"}
            )
        else:
            from app.services.admin_service import AdminService

            data["counts"] = AdminService(self.db).dashboard_stats()
            data["logs"] = AdminService(self.db).audit_logs(10)
        return data
