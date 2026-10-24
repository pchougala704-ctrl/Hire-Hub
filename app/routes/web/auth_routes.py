from flask import flash, redirect, render_template, request, session, url_for

from app.exceptions import HireHubError
from app.extensions import get_db
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.routes.web import auth_bp


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            user = AuthService(get_db()).register(request.form)
            session.clear()
            session["user_id"] = str(user["_id"])
            session["role"] = user["role"]
            session.permanent = True
            flash("Your account has been created.", "success")
            return redirect(url_for("web.dashboard"))
        except HireHubError as exc:
            flash(str(exc), "danger")
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user = AuthService(get_db()).login(request.form.get("email"), request.form.get("password"))
            session.clear()
            session["user_id"] = str(user["_id"])
            session["role"] = user["role"]
            session.permanent = True
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("web.dashboard")
            return redirect(next_url)
        except HireHubError as exc:
            flash(str(exc), "danger")
    return render_template("auth/login.html")


@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        try:
            user = AuthService(get_db()).login(
                request.form.get("email"),
                request.form.get("password"),
            )
            if user.get("role") != "ADMIN":
                flash("This sign-in page is for administrator accounts.", "danger")
                return render_template("auth/admin_login.html"), 403
            session.clear()
            session["user_id"] = str(user["_id"])
            session["role"] = user["role"]
            session.permanent = True
            return redirect(url_for("web.admin_dashboard"))
        except HireHubError as exc:
            flash(str(exc), "danger")
    return render_template("auth/admin_login.html")


@auth_bp.post("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        AuditService(get_db()).record(user_id, "USER_LOGOUT", "user", user_id)
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("web.index"))
