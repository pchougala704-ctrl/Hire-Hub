from app.services.job_service import JobService
from app.services.matching_service import MatchingService


class RecommendationService:
    def __init__(self, db):
        self.db = db

    def for_candidate(self, user, limit=10):
        profile = self.db["candidates"].find_one({"user_email": user["email"]}) or {}
        jobs, _ = JobService(self.db).search({}, 1, min(50, max(limit, 10)))
        ranked = [
            {"job": job, "match": MatchingService.score(profile, job)}
            for job in jobs
        ]
        ranked.sort(key=lambda item: item["match"]["score"], reverse=True)
        return ranked[:limit]
