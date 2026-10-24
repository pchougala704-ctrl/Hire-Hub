from datetime import datetime, timezone
import secrets

from flask import current_app, request, send_from_directory, session

from app.exceptions import UnauthorizedError, ValidationError
from app.extensions import get_db
from app.services.application_service import ApplicationService
from app.services.admin_service import AdminService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.candidate_service import CandidateService
from app.services.company_service import CompanyService
from app.services.job_service import JobService
from app.services.matching_service import MatchingService
from app.services.interview_service import InterviewService
from app.services.resume_service import ResumeService
from app.services.recommendation_service import RecommendationService
from app.utils import api_response, current_user, json_body, json_safe, login_required, role_required
from app.routes.api import api_bp


@api_bp.get("/auth/csrf")
def csrf():
    from app.utils import csrf_token
    return api_response({"csrf_token": csrf_token()}, "CSRF token")


@api_bp.post("/auth/register")
def register():
    user = AuthService(get_db()).register(json_body())
    session.clear()
    session["user_id"] = str(user["_id"])
    session["role"] = user["role"]
    session.permanent = True
    session["csrf_token"] = secrets.token_urlsafe(32)
    return api_response({"user": json_safe(user), "csrf_token": session["csrf_token"]}, "Account created", 201)


@api_bp.post("/auth/login")
def login():
    values = json_body()
    user = AuthService(get_db()).login(values.get("email"), values.get("password"))
    session.clear()
    session["user_id"] = str(user["_id"])
    session["role"] = user["role"]
    session.permanent = True
    session["csrf_token"] = secrets.token_urlsafe(32)
    return api_response({"user": json_safe(user), "csrf_token": session["csrf_token"]}, "Signed in")


@api_bp.post("/auth/logout")
@login_required
def logout():
    user = current_user()
    AuditService(get_db()).record(user["_id"], "USER_LOGOUT", "user", user["_id"])
    session.clear()
    return api_response(message="Signed out")


@api_bp.get("/auth/me")
@login_required
def me():
    return api_response(json_safe(current_user()))


@api_bp.get("/jobs")
def jobs():
    filters = {key: request.args.get(key) for key in (
        "keyword", "skill", "location", "work_mode", "employment_type", "company_id",
        "salary_min", "experience_min",
    )}
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError) as exc:
        raise ValidationError("Page must be a whole number.") from exc
    items, total = JobService(get_db()).search(filters, page)
    return api_response({"items": json_safe(items), "total": total, "page": page})


@api_bp.get("/jobs/<job_id>")
def job(job_id):
    result = JobService(get_db()).get(job_id)
    user = current_user()
    if user and user["role"] == "CANDIDATE":
        candidate = CandidateService(get_db()).get_profile(user)
        result["match"] = MatchingService.score(candidate, result)
    return api_response(json_safe(result))


@api_bp.post("/jobs")
@role_required("RECRUITER")
def create_job():
    job_id = JobService(get_db()).create(json_body(), current_user())
    AuditService(get_db()).record(current_user()["_id"], "JOB_CREATED", "job", job_id)
    return api_response({"id": str(job_id)}, "Job created", 201)


@api_bp.put("/jobs/<job_id>")
@role_required("RECRUITER", "ADMIN")
def update_job(job_id):
    db = get_db()
    user = current_user()
    values = json_body()
    updated = JobService(db).update(job_id, values, user)
    AuditService(db).record(user["_id"], "JOB_UPDATED", "job", job_id)
    return api_response(json_safe(updated), "Job updated")


@api_bp.delete("/jobs/<job_id>")
@role_required("RECRUITER", "ADMIN")
def close_job(job_id):
    JobService(get_db()).close(job_id, current_user())
    AuditService(get_db()).record(current_user()["_id"], "JOB_CLOSED", "job", job_id)
    return api_response(message="Job closed")


@api_bp.post("/jobs/<job_id>/apply")
@role_required("CANDIDATE")
def apply(job_id):
    application_id = ApplicationService(get_db()).apply(job_id, current_user())
    return api_response({"id": str(application_id)}, "Application submitted successfully", 201)


@api_bp.get("/applications")
@login_required
def applications():
    user = current_user()
    docs = ApplicationService(get_db()).list_for_user(user, 100)
    return api_response(json_safe(docs))


@api_bp.get("/applications/<application_id>")
@login_required
def application(application_id):
    return api_response(json_safe(ApplicationService(get_db()).get_for_user(application_id, current_user())))


@api_bp.put("/applications/<application_id>/status")
@login_required
def update_application(application_id):
    values = json_body()
    item = ApplicationService(get_db()).update_status(application_id, values.get("status", ""), current_user())
    return api_response(json_safe(item), "Application status updated")


@api_bp.get("/candidates/<candidate_id>")
@login_required
def candidate_profile(candidate_id):
    result = CandidateService(get_db()).get_profile_for_viewer(candidate_id, current_user())
    return api_response(json_safe(result))


@api_bp.get("/candidates")
@role_required("RECRUITER")
def search_candidates():
    results = CandidateService(get_db()).search({
        "skills": request.args.get("skill", ""),
        "location": request.args.get("location", ""),
    })
    return api_response(json_safe(results))


@api_bp.put("/candidates/<candidate_id>")
@role_required("CANDIDATE")
def update_candidate_profile(candidate_id):
    oid = AuthService.object_id(candidate_id)
    user = current_user()
    if user["_id"] != oid:
        raise UnauthorizedError("You can only update your own profile.")
    profile = CandidateService(get_db()).update_api_profile(json_body(), user)
    return api_response(json_safe(profile), "Profile updated")


@api_bp.get("/recommendations")
@role_required("CANDIDATE")
def recommendations():
    result = RecommendationService(get_db()).for_candidate(current_user())
    return api_response(json_safe(result))


@api_bp.get("/saved-jobs")
@role_required("CANDIDATE")
def saved_jobs():
    jobs = CandidateService(get_db()).saved_jobs(current_user())
    return api_response(json_safe(jobs))


@api_bp.get("/company")
@role_required("RECRUITER")
def company_profile():
    company = CompanyService(get_db()).get_for_recruiter(current_user())
    if not company:
        raise ValidationError("Company profile not found.")
    return api_response(json_safe(company))


@api_bp.put("/company")
@role_required("RECRUITER")
def update_company_profile():
    company = CompanyService(get_db()).update_for_recruiter(json_body(), current_user())
    return api_response(json_safe(company), "Company profile updated")


@api_bp.post("/interviews")
@role_required("RECRUITER")
def create_interview():
    values = json_body()
    interview = InterviewService(get_db()).schedule(
        values.get("application_id", ""), values, current_user()
    )
    return api_response(json_safe(interview), "Interview scheduled", 201)


@api_bp.get("/interviews")
@login_required
def interviews():
    user = current_user()
    return api_response(json_safe(InterviewService(get_db()).list_for_user(user)))


@api_bp.put("/interviews/<interview_id>")
@login_required
def update_interview(interview_id):
    values = json_body()
    interview = InterviewService(get_db()).update(interview_id, values, current_user())
    return api_response(json_safe(interview), "Interview updated")


@api_bp.post("/resumes")
@role_required("CANDIDATE")
def upload_resume():
    user = current_user()
    resume = ResumeService(get_db(), current_app.config["UPLOAD_FOLDER"]).upload(request.files.get("file"), user)
    AuditService(get_db()).record(user["_id"], "RESUME_UPLOADED", "resume", resume["_id"])
    return api_response(json_safe(resume), "Resume uploaded", 201)


@api_bp.get("/resumes/<resume_id>")
@login_required
def download_resume(resume_id):
    user = current_user()
    resume = ResumeService(get_db(), current_app.config["UPLOAD_FOLDER"]).get_for_user(resume_id, user)
    if not resume:
        from app.exceptions import ResumeUploadError
        raise ResumeUploadError("Resume not found.")
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        resume["stored_name"],
        as_attachment=True,
        download_name=resume["original_name"],
        mimetype=resume["mime_type"],
    )


@api_bp.delete("/resumes/<resume_id>")
@role_required("CANDIDATE", "ADMIN")
def delete_resume(resume_id):
    user = current_user()
    resume_service = ResumeService(get_db(), current_app.config["UPLOAD_FOLDER"])
    if not resume_service.delete(resume_id, user):
        raise ValidationError("Resume not found.")
    return api_response(message="Resume deleted")


@api_bp.get("/analytics/<role>")
@login_required
def analytics(role):
    user = current_user()
    result = AnalyticsService(get_db()).for_role(role, user)
    return api_response(json_safe(result))


@api_bp.get("/admin/users")
@role_required("ADMIN")
def admin_users():
    users = AdminService(get_db()).list_users()
    return api_response(json_safe(users))


@api_bp.put("/admin/users/<user_id>/active")
@role_required("ADMIN")
def set_user_active(user_id):
    active = json_body().get("active")
    oid = AdminService(get_db()).set_user_active(user_id, active, current_user())
    AuditService(get_db()).record(current_user()["_id"], "USER_ACTIVATED" if active else "USER_DEACTIVATED", "user", oid)
    return api_response(message="User status updated")


@api_bp.get("/admin/companies")
@role_required("ADMIN")
def admin_companies():
    companies = AdminService(get_db()).list_companies()
    return api_response(json_safe(companies))


@api_bp.put("/admin/companies/<company_id>/verification")
@role_required("ADMIN")
def verify_company(company_id):
    verified = json_body().get("verified")
    oid = AdminService(get_db()).set_company_verified(company_id, verified)
    AuditService(get_db()).record(current_user()["_id"], "COMPANY_VERIFIED" if verified else "COMPANY_UNVERIFIED", "company", oid)
    return api_response(message="Company verification updated")


@api_bp.put("/admin/jobs/<job_id>/status")
@role_required("ADMIN")
def moderate_job(job_id):
    status = json_body().get("status", "")
    oid = JobService(get_db()).moderate(job_id, status)
    AuditService(get_db()).record(current_user()["_id"], "JOB_MODERATED", "job", oid, {"status": status})
    return api_response(message="Job status updated")


@api_bp.get("/admin/audit-logs")
@role_required("ADMIN")
def audit_logs():
    values = AdminService(get_db()).audit_logs()
    return api_response(json_safe(values))
