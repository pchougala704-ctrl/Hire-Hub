import csv
from io import StringIO

from bson import ObjectId
from flask import Response, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for

from app.exceptions import HireHubError
from app.extensions import get_db
from app.services.application_service import ApplicationService
from app.services.admin_service import AdminService
from app.services.audit_service import AuditService
from app.services.candidate_service import CandidateService
from app.services.dashboard_service import DashboardService
from app.services.job_service import JobService
from app.services.interview_service import InterviewService
from app.services.company_service import CompanyService
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.services.resume_service import ResumeService
from app.utils import current_user, login_required, role_required
from app.routes.web import web_bp


def _csv_response(filename, headers, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        safe_row = []
        for value in row:
            value = value.isoformat() if hasattr(value, "isoformat") else str(value or "")
            if value.startswith(("=", "+", "-", "@", "\t", "\r")):
                value = "'" + value
            safe_row.append(value)
        writer.writerow(safe_row)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@web_bp.get("/")
def index():
    jobs, _ = JobService(get_db()).search({}, 1, 6)
    return render_template("home.html", jobs=jobs)


@web_bp.get("/jobs")
def jobs():
    filters = {key: request.args.get(key, "") for key in ("keyword", "skill", "location", "work_mode", "employment_type")}
    try:
        page = max(1, int(request.args.get("page", "1")))
        results, total = JobService(get_db()).search(filters, page)
    except (ValueError, HireHubError) as exc:
        flash(str(exc), "danger")
        results, total, page = [], 0, 1
    return render_template("jobs/list.html", jobs=results, total=total, page=page, filters=filters)


@web_bp.get("/jobs/<job_id>")
def job_detail(job_id):
    try:
        job = JobService(get_db()).get(job_id)
    except HireHubError:
        abort(404)
    match = None
    user = current_user()
    if user and user["role"] == "CANDIDATE":
        candidate = CandidateService(get_db()).get_profile(user)
        match = MatchingService.score(candidate, job)
    return render_template("jobs/detail.html", job=job, match=match)


@web_bp.post("/jobs/<job_id>/apply")
@role_required("CANDIDATE")
def apply_job(job_id):
    try:
        ApplicationService(get_db()).apply(job_id, current_user())
        flash("Application submitted.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.job_detail", job_id=job_id))


@web_bp.post("/jobs/<job_id>/save")
@role_required("CANDIDATE")
def save_job(job_id):
    if not ObjectId.is_valid(job_id):
        abort(404)
    saved = CandidateService(get_db()).toggle_saved_job(job_id, current_user())
    flash("Job saved." if saved else "Job removed from saved jobs.", "success" if saved else "info")
    return redirect(url_for("web.job_detail", job_id=job_id))


@web_bp.get("/saved-jobs")
@role_required("CANDIDATE")
def saved_jobs():
    jobs = CandidateService(get_db()).saved_jobs(current_user())
    return render_template("candidate/saved_jobs.html", jobs=jobs)


@web_bp.get("/dashboard")
@login_required
def dashboard():
    user = current_user()
    data = DashboardService(get_db()).for_user(user)
    return render_template("dashboard/index.html", user=user, data=data)


@web_bp.get("/admin/dashboard")
@role_required("ADMIN")
def admin_dashboard():
    user = current_user()
    data = DashboardService(get_db()).for_user(user)
    return render_template("dashboard/index.html", user=user, data=data)


@web_bp.get("/profile")
@role_required("CANDIDATE")
def profile():
    user = current_user()
    candidate = CandidateService(get_db()).get_profile(user)
    return render_template("candidate/profile.html", user=user, candidate=candidate)


@web_bp.route("/resume", methods=["GET", "POST"])
@role_required("CANDIDATE")
def resume():
    user = current_user()
    service = ResumeService(get_db(), current_app.config["UPLOAD_FOLDER"])
    if request.method == "POST":
        try:
            uploaded = service.upload(request.files.get("file"), user)
            from app.services.audit_service import AuditService
            AuditService(get_db()).record(user["_id"], "RESUME_UPLOADED", "resume", uploaded["_id"])
            flash("Resume uploaded.", "success")
        except HireHubError as exc:
            flash(str(exc), "danger")
    candidate = CandidateService(get_db()).get_profile(user)
    stored = None
    if candidate.get("resume_id"):
        try:
            stored = service.get_for_user(candidate["resume_id"], user)
        except HireHubError:
            stored = None
    return render_template("candidate/resume.html", resume=stored)


@web_bp.get("/resume/<resume_id>/download")
@role_required("CANDIDATE", "RECRUITER", "ADMIN")
def download_resume(resume_id):
    user = current_user()
    stored = ResumeService(get_db(), current_app.config["UPLOAD_FOLDER"]).get_for_user(resume_id, user)
    if not stored:
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], stored["stored_name"],
        as_attachment=True, download_name=stored["original_name"], mimetype=stored["mime_type"],
    )


@web_bp.post("/profile")
@role_required("CANDIDATE")
def update_profile():
    user = current_user()
    try:
        CandidateService(get_db()).update_web_profile(request.form, user)
    except HireHubError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("web.profile"))
    flash("Profile saved.", "success")
    return redirect(url_for("web.profile"))


@web_bp.get("/applications")
@login_required
def applications():
    user = current_user()
    items = ApplicationService(get_db()).list_with_jobs(user, 100)
    return render_template("applications/list.html", applications=items, user=user)


@web_bp.post("/applications/<application_id>/status")
@login_required
def update_application_status(application_id):
    try:
        ApplicationService(get_db()).update_status(application_id, request.form.get("status", ""), current_user())
        flash("Application status updated.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.applications"))


@web_bp.post("/applications/<application_id>/interview")
@role_required("RECRUITER")
def schedule_interview(application_id):
    try:
        InterviewService(get_db()).schedule(application_id, request.form, current_user())
        flash("Interview scheduled.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.applications"))


@web_bp.get("/interviews")
@login_required
def interviews():
    user = current_user()
    items = InterviewService(get_db()).list_for_user(user)
    return render_template("interviews/list.html", interviews=items)


@web_bp.get("/notifications")
@login_required
def notifications():
    user = current_user()
    service = NotificationService(get_db())
    items = service.list_for_user(user)
    service.mark_all_read(user)
    return render_template("notifications/list.html", notifications=items)


@web_bp.route("/recruiter/jobs/new", methods=["GET", "POST"])
@role_required("RECRUITER")
def create_job():
    if request.method == "POST":
        try:
            job_id = JobService(get_db()).create(request.form, current_user())
            from app.services.audit_service import AuditService
            AuditService(get_db()).record(current_user()["_id"], "JOB_CREATED", "job", job_id)
            flash("Job published.", "success")
            return redirect(url_for("web.my_jobs"))
        except HireHubError as exc:
            flash(str(exc), "danger")
    return render_template("recruiter/job_form.html")


@web_bp.get("/recruiter/jobs")
@role_required("RECRUITER")
def my_jobs():
    jobs = JobService(get_db()).for_recruiter(current_user())
    return render_template("recruiter/jobs.html", jobs=jobs)


@web_bp.get("/recruiter/candidates")
@role_required("RECRUITER")
def search_candidates():
    profiles = CandidateService(get_db()).search({
        "skills": request.args.get("skill", ""),
        "location": request.args.get("location", ""),
    })
    return render_template("recruiter/candidates.html", profiles=profiles)


@web_bp.route("/recruiter/jobs/<job_id>/edit", methods=["GET", "POST"])
@role_required("RECRUITER")
def edit_job(job_id):
    user = current_user()
    service = JobService(get_db())
    try:
        job = service.get(job_id)
        if str(job["recruiter_id"]) != str(user["_id"]):
            abort(403)
        if request.method == "POST":
            job = service.update(job_id, request.form, user)
            AuditService(get_db()).record(user["_id"], "JOB_UPDATED", "job", job_id)
            flash("Job updated.", "success")
            return redirect(url_for("web.my_jobs"))
    except HireHubError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("web.my_jobs"))
    return render_template("recruiter/job_form.html", job=job)


@web_bp.route("/company", methods=["GET", "POST"])
@role_required("RECRUITER")
def company_profile():
    service = CompanyService(get_db())
    if request.method == "POST":
        try:
            service.update_for_recruiter(request.form, current_user())
            flash("Company profile saved.", "success")
        except HireHubError as exc:
            flash(str(exc), "danger")
    return render_template("recruiter/company.html", company=service.get_for_recruiter(current_user()))


@web_bp.post("/recruiter/jobs/<job_id>/close")
@role_required("RECRUITER")
def close_job(job_id):
    try:
        JobService(get_db()).close(job_id, current_user())
        from app.services.audit_service import AuditService
        AuditService(get_db()).record(current_user()["_id"], "JOB_CLOSED", "job", job_id)
        flash("Job closed.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.my_jobs"))


@web_bp.get("/admin/users")
@role_required("ADMIN")
def admin_users():
    users = AdminService(get_db()).list_users()
    return render_template("admin/users.html", users=users)


@web_bp.get("/admin/candidates")
@role_required("ADMIN")
def admin_candidates():
    users = AdminService(get_db()).list_users(role="CANDIDATE")
    return render_template("admin/people.html", users=users, page_title="Candidates")


@web_bp.get("/admin/recruiters")
@role_required("ADMIN")
def admin_recruiters():
    users = AdminService(get_db()).list_users(role="RECRUITER")
    return render_template("admin/people.html", users=users, page_title="Recruiters")


@web_bp.get("/admin/jobs")
@role_required("ADMIN")
def admin_jobs():
    jobs = AdminService(get_db()).list_jobs()
    return render_template("admin/jobs.html", jobs=jobs)


@web_bp.post("/admin/jobs/<job_id>/status")
@role_required("ADMIN")
def admin_update_job_status(job_id):
    status = request.form.get("status", "")
    try:
        oid = JobService(get_db()).moderate(job_id, status)
        AuditService(get_db()).record(current_user()["_id"], "JOB_MODERATED", "job", oid, {"status": status})
        flash("Job status updated.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.admin_jobs"))


@web_bp.get("/admin/applications")
@role_required("ADMIN")
def admin_applications():
    applications = ApplicationService(get_db()).list_with_jobs(current_user(), 200)
    return render_template("applications/list.html", applications=applications, user=current_user())


@web_bp.get("/admin/companies")
@role_required("ADMIN")
def admin_companies():
    companies = AdminService(get_db()).list_companies()
    return render_template("admin/companies.html", companies=companies)


@web_bp.post("/admin/companies/<company_id>/verification")
@role_required("ADMIN")
def verify_company(company_id):
    try:
        verified = request.form.get("verified") == "true"
        oid = AdminService(get_db()).set_company_verified(company_id, verified)
        AuditService(get_db()).record(current_user()["_id"], "COMPANY_VERIFIED" if verified else "COMPANY_UNVERIFIED", "company", oid)
        flash("Company verification updated.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.admin_companies"))


@web_bp.get("/admin/audit-logs")
@role_required("ADMIN")
def admin_audit_logs():
    logs = AdminService(get_db()).audit_logs()
    return render_template("admin/audit_logs.html", logs=logs)


@web_bp.get("/admin/reports")
@role_required("ADMIN")
def admin_reports():
    return render_template("admin/reports.html")


@web_bp.post("/admin/users/<user_id>/active")
@role_required("ADMIN")
def set_user_active(user_id):
    try:
        active = request.form.get("active") == "true"
        oid = AdminService(get_db()).set_user_active(user_id, active, current_user())
        AuditService(get_db()).record(current_user()["_id"], "USER_ACTIVATED" if active else "USER_DEACTIVATED", "user", oid)
        flash("User status updated.", "success")
    except HireHubError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("web.admin_users"))


@web_bp.get("/admin/reports/applications.csv")
@role_required("ADMIN")
def application_report():
    return _csv_response(
        "hirehub-applications.csv",
        ["application_id", "candidate_id", "job_id", "status", "applied_at"],
        ReportService(get_db()).applications(request.args),
    )


@web_bp.get("/admin/reports/candidates.csv")
@role_required("ADMIN")
def candidate_report():
    return _csv_response(
        "hirehub-candidates.csv",
        ["user_id", "name", "email", "location", "created_at"],
        ReportService(get_db()).candidates(request.args),
    )


@web_bp.get("/admin/reports/jobs.csv")
@role_required("ADMIN")
def job_report():
    return _csv_response(
        "hirehub-jobs.csv",
        ["job_id", "title", "company_id", "location", "work_mode", "employment_type", "status", "created_at"],
        ReportService(get_db()).jobs(request.args),
    )


@web_bp.get("/admin/reports/skills.csv")
@role_required("ADMIN")
def skill_report():
    return _csv_response(
        "hirehub-skill-demand.csv",
        ["skill", "open_openings"],
        ReportService(get_db()).skills(request.args),
    )


@web_bp.get("/admin/reports/recruitment.csv")
@role_required("ADMIN")
def recruitment_report():
    return _csv_response(
        "hirehub-recruitment.csv",
        ["recruiter_id", "name", "email", "jobs", "applications", "selections"],
        ReportService(get_db()).recruitment(),
    )
