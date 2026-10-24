import random
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import create_app

app = create_app()
randomizer = random.Random(42)
skill_pool = ["Python", "SQL", "MongoDB", "JavaScript", "React", "Flask", "AWS", "Docker", "Figma", "Tableau"]
locations = ["Bengaluru", "Mumbai", "Pune", "Hyderabad", "Remote"]
job_titles = ["Software Engineer", "Data Analyst", "Product Designer", "Backend Developer", "Frontend Engineer"]

with app.app_context():
    db = app.extensions["mongo_db"]
    if db["users"].count_documents({}):
        raise SystemExit("Refusing to seed a non-empty users collection.")

    now = datetime.now(timezone.utc)
    password_hash = generate_password_hash("ChangeMe123!")
    companies = [
        db["companies"].insert_one({
            "name": f"Northstar {name}",
            "verified": index < 3,
            "created_at": now,
        }).inserted_id
        for index, name in enumerate(["Labs", "Systems", "Analytics", "Design", "Digital"])
    ]

    recruiter_ids = []
    for index in range(10):
        email = f"recruiter{index + 1:02d}@example.test"
        recruiter_id = db["users"].insert_one({
            "name": f"Recruiter {index + 1}",
            "email": email,
            "role": "RECRUITER",
            "active": True,
            "company_id": str(companies[index % len(companies)]),
            "password_hash": password_hash,
            "created_at": now,
        }).inserted_id
        recruiter_ids.append(recruiter_id)
        db["recruiters"].insert_one({
            "user_email": email,
            "company_id": str(companies[index % len(companies)]),
        })

    candidate_ids = []
    for index in range(20):
        email = f"candidate{index + 1:02d}@example.test"
        candidate_id = db["users"].insert_one({
            "name": f"Candidate {index + 1}",
            "email": email,
            "role": "CANDIDATE",
            "active": True,
            "password_hash": password_hash,
            "created_at": now,
        }).inserted_id
        candidate_ids.append(candidate_id)
        db["candidates"].insert_one({
            "user_email": email,
            "location": randomizer.choice(locations),
            "skills": randomizer.sample(skill_pool, 3),
            "saved_jobs": [],
        })

    job_ids = []
    for index in range(30):
        job_id = db["jobs"].insert_one({
            "title": f"{randomizer.choice(job_titles)} {index + 1}",
            "description": "Join a collaborative team building useful products. Bring your ideas and grow your craft.",
            "skills": randomizer.sample(skill_pool, 3),
            "location": randomizer.choice(locations),
            "work_mode": randomizer.choice(["REMOTE", "HYBRID", "ONSITE"]),
            "employment_type": randomizer.choice(["FULL_TIME", "PART_TIME", "INTERNSHIP", "CONTRACT"]),
            "recruiter_id": str(recruiter_ids[index % len(recruiter_ids)]),
            "company_id": str(companies[index % len(companies)]),
            "salary_min": randomizer.randrange(50000, 100001, 5000),
            "salary_max": randomizer.randrange(110000, 180001, 5000),
            "experience_min": randomizer.randrange(0, 5),
            "experience_max": randomizer.randrange(5, 11),
            "status": "OPEN",
            "created_at": now - timedelta(days=randomizer.randrange(1, 90)),
            "updated_at": now,
        }).inserted_id
        job_ids.append(job_id)

    combinations = [(candidate_id, job_id) for candidate_id in candidate_ids for job_id in job_ids]
    randomizer.shuffle(combinations)
    application_ids = []
    for candidate_id, job_id in combinations[:50]:
        job = db["jobs"].find_one({"_id": job_id})
        applied_at = now - timedelta(days=randomizer.randrange(0, 30))
        application_id = db["applications"].insert_one({
            "candidate_id": str(candidate_id),
            "job_id": str(job_id),
            "recruiter_id": job["recruiter_id"],
            "status": randomizer.choice(["APPLIED", "UNDER_REVIEW", "SHORTLISTED", "REJECTED"]),
            "applied_at": applied_at,
            "updated_at": applied_at,
            "recruiter_notes": "",
        }).inserted_id
        application_ids.append((application_id, candidate_id, job["recruiter_id"]))

    for application_id, candidate_id, recruiter_id in application_ids[:15]:
        interview_id = db["interviews"].insert_one({
            "application_id": str(application_id),
            "candidate_id": str(candidate_id),
            "recruiter_id": recruiter_id,
            "date": (now + timedelta(days=randomizer.randrange(1, 30))).date().isoformat(),
            "time": f"{randomizer.randrange(9, 17):02d}:00",
            "type": randomizer.choice(["ONLINE", "PHONE", "IN_PERSON"]),
            "status": "SCHEDULED",
            "feedback": "",
        }).inserted_id
        db["applications"].update_one({"_id": application_id}, {"$set": {
            "status": "INTERVIEW_SCHEDULED",
            "interview_id": str(interview_id),
        }})

    print("Seeded 20 candidates, 10 recruiters, 5 companies, 30 jobs, 50 applications, and 15 interviews.")
    print("Development account password: ChangeMe123! (change it before using non-local data)")
