from uuid import uuid4

import pytest
from pymongo.errors import ServerSelectionTimeoutError
from werkzeug.security import check_password_hash

from app import create_app
from app.exceptions import ValidationError
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService


@pytest.fixture
def admin_app():
    database_name = f"hirehub_admin_test_{uuid4().hex}"
    app = create_app({
        "SECRET_KEY": "admin-test-secret",
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DATABASE": database_name,
    })
    client = app.extensions["mongo_client"]
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        client.close()
        pytest.skip("MongoDB is not available for admin integration tests.")
    yield app
    client.drop_database(database_name)
    client.close()


def test_dashboard_stats_use_database_counts(admin_app):
    db = admin_app.extensions["mongo_db"]
    db["users"].insert_many([
        {"role": "ADMIN", "active": True},
        {"role": "CANDIDATE"},
        {"role": "RECRUITER"},
    ])
    db["companies"].insert_one({"name": "Example"})
    db["jobs"].insert_many([
        {"status": "OPEN"},
        {"status": "CLOSED"},
    ])
    db["applications"].insert_many([
        {"status": "SELECTED"},
        {"status": "APPLIED"},
    ])
    db["interviews"].insert_one({"status": "SCHEDULED"})

    stats = AdminService(db).dashboard_stats()

    assert stats["users"] == 3
    assert stats["candidates"] == 1
    assert stats["recruiters"] == 1
    assert stats["companies"] == 1
    assert stats["jobs"] == 2
    assert stats["open_jobs"] == 1
    assert stats["applications"] == 2
    assert stats["interviews"] == 1
    assert stats["selections"] == 1
    assert {item["_id"]: item["count"] for item in stats["applications_by_status"]} == {
        "APPLIED": 1,
        "SELECTED": 1,
    }


def test_local_admin_creation_hashes_password_and_audits(admin_app):
    db = admin_app.extensions["mongo_db"]

    user = AdminService(db).create_admin(
        "Local Admin",
        "ADMIN@example.test",
        "A-very-secure-password",
    )

    assert user["role"] == "ADMIN"
    assert user["email"] == "admin@example.test"
    assert check_password_hash(user["password_hash"], "A-very-secure-password")
    assert user["password_hash"] != "A-very-secure-password"
    assert db["audit_logs"].count_documents({
        "action": "ADMIN_ACCOUNT_CREATED",
        "user_id": str(user["_id"]),
    }) == 1

    client = admin_app.test_client()
    csrf = client.get("/api/auth/csrf").json["data"]["csrf_token"]
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": csrf,
            "email": "admin@example.test",
            "password": "A-very-secure-password",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")


def test_public_registration_cannot_create_admin(admin_app):
    with pytest.raises(ValidationError, match="Public registration"):
        AuthService(admin_app.extensions["mongo_db"]).register({
            "name": "Public Admin",
            "email": "public-admin@example.test",
            "password": "A-very-secure-password",
            "confirm_password": "A-very-secure-password",
            "role": "ADMIN",
        })
    assert admin_app.extensions["mongo_db"]["users"].count_documents({}) == 0


def test_admin_pages_require_admin_role(admin_app):
    db = admin_app.extensions["mongo_db"]
    candidate_id = db["users"].insert_one({
        "name": "Candidate",
        "email": "candidate@example.test",
        "role": "CANDIDATE",
        "active": True,
    }).inserted_id
    client = admin_app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = str(candidate_id)
        session["role"] = "CANDIDATE"

    for path in (
        "/admin/dashboard",
        "/admin/candidates",
        "/admin/recruiters",
        "/admin/jobs",
        "/admin/applications",
        "/admin/users",
    ):
        response = client.get(path)
        assert response.status_code == 403
    assert client.get("/api/admin/users").status_code == 403


def test_admin_dashboard_renders_real_statistics(admin_app):
    db = admin_app.extensions["mongo_db"]
    admin_id = db["users"].insert_one({
        "name": "Administrator",
        "email": "admin@example.test",
        "role": "ADMIN",
        "active": True,
    }).inserted_id
    db["users"].insert_one({"role": "CANDIDATE", "active": True})
    db["jobs"].insert_one({"status": "OPEN"})
    client = admin_app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = str(admin_id)
        session["role"] = "ADMIN"

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b"Candidates" in response.data
    assert b"Open Jobs" in response.data


def test_admin_can_manage_candidates_jobs_and_applications(admin_app):
    db = admin_app.extensions["mongo_db"]
    admin_id = db["users"].insert_one({
        "name": "Administrator",
        "email": "admin@example.test",
        "role": "ADMIN",
        "active": True,
    }).inserted_id
    candidate_id = db["users"].insert_one({
        "name": "Candidate",
        "email": "candidate@example.test",
        "role": "CANDIDATE",
        "active": True,
    }).inserted_id
    recruiter_id = db["users"].insert_one({
        "name": "Recruiter",
        "email": "recruiter@example.test",
        "role": "RECRUITER",
        "active": True,
    }).inserted_id
    job_id = db["jobs"].insert_one({
        "title": "Engineer",
        "description": "Build things",
        "status": "OPEN",
        "skills": ["Python"],
        "recruiter_id": str(recruiter_id),
    }).inserted_id
    application_id = db["applications"].insert_one({
        "candidate_id": str(candidate_id),
        "recruiter_id": str(recruiter_id),
        "job_id": str(job_id),
        "status": "APPLIED",
    }).inserted_id
    client = admin_app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = str(admin_id)
        session["role"] = "ADMIN"
        session["csrf_token"] = "admin-test-csrf"

    for path in ("/admin/dashboard", "/admin/candidates", "/admin/recruiters", "/admin/jobs", "/admin/applications"):
        assert client.get(path).status_code == 200

    job_response = client.post(
        f"/admin/jobs/{job_id}/status",
        data={"csrf_token": "admin-test-csrf", "status": "CLOSED"},
    )
    application_response = client.post(
        f"/applications/{application_id}/status",
        data={"csrf_token": "admin-test-csrf", "status": "SHORTLISTED"},
    )
    user_response = client.post(
        f"/admin/users/{candidate_id}/active",
        data={"csrf_token": "admin-test-csrf", "active": "false"},
    )

    assert job_response.status_code == 302
    assert application_response.status_code == 302
    assert user_response.status_code == 302
    assert db["jobs"].find_one({"_id": job_id})["status"] == "CLOSED"
    assert db["applications"].find_one({"_id": application_id})["status"] == "SHORTLISTED"
    assert db["users"].find_one({"_id": candidate_id})["active"] is False
    assert db["audit_logs"].count_documents({"action": "JOB_MODERATED"}) == 1


def test_last_active_admin_cannot_be_deactivated(admin_app):
    db = admin_app.extensions["mongo_db"]
    target_id = db["users"].insert_one({
        "email": "admin@example.test",
        "role": "ADMIN",
        "active": True,
    }).inserted_id
    with pytest.raises(ValidationError, match="last active administrator"):
        AdminService(db).set_user_active(str(target_id), False)

    assert db["users"].find_one({"_id": target_id})["active"] is True
