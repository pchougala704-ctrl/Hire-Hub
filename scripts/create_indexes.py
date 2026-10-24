from app import create_app

app = create_app()
with app.app_context():
    db = app.extensions["mongo_db"]
    db["users"].create_index("email", unique=True)
    db["jobs"].create_index([("title", "text"), ("description", "text"), ("skills", "text")])
    db["jobs"].create_index("location")
    db["jobs"].create_index("skills")
    db["jobs"].create_index([("status", 1), ("created_at", -1)])
    db["applications"].create_index([("candidate_id", 1), ("job_id", 1)], unique=True)
    db["applications"].create_index("candidate_id")
    db["applications"].create_index("job_id")
    db["applications"].create_index("recruiter_id")
    db["interviews"].create_index("application_id")
    db["notifications"].create_index([("user_id", 1), ("created_at", -1)])
    print("HireHub indexes created.")
