class MatchingService:
    @staticmethod
    def score(candidate, job):
        candidate_skills = {str(skill).strip().lower() for skill in candidate.get("skills", [])}
        job_skills = {str(skill).strip().lower() for skill in job.get("skills", [])}
        matched = sorted(candidate_skills & job_skills)
        missing = sorted(job_skills - candidate_skills)
        skill_score = len(matched) / len(job_skills) if job_skills else 1
        criteria = [(skill_score, 0.75)]
        candidate_location = str(candidate.get("location", "")).strip().lower()
        if candidate_location:
            location_match = (
                job.get("work_mode") == "REMOTE"
                or candidate_location == str(job.get("location", "")).strip().lower()
            )
            criteria.append((1.0 if location_match else 0.0, 0.1))
        experience = candidate.get("experience_years")
        if experience is not None and (job.get("experience_min") is not None or job.get("experience_max") is not None):
            minimum = job.get("experience_min") or 0
            maximum = job.get("experience_max")
            in_range = experience >= minimum and (maximum is None or experience <= maximum)
            criteria.append((1.0 if in_range else 0.0, 0.05))
        expected_salary = candidate.get("expected_salary")
        if expected_salary is not None and (job.get("salary_min") is not None or job.get("salary_max") is not None):
            minimum = job.get("salary_min") or 0
            maximum = job.get("salary_max")
            in_range = expected_salary >= minimum and (maximum is None or expected_salary <= maximum)
            criteria.append((1.0 if in_range else 0.0, 0.05))
        preferred_mode = str(candidate.get("preferred_work_mode", "")).upper()
        if preferred_mode:
            criteria.append((1.0 if preferred_mode == job.get("work_mode") else 0.0, 0.05))
        total_weight = sum(weight for _, weight in criteria)
        score = round(sum(value * weight for value, weight in criteria) / total_weight * 100)
        return {"score": score, "matched_skills": matched, "missing_skills": missing}
