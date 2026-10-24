import secrets
from functools import wraps

from bson import ObjectId
from flask import abort, current_app, jsonify, redirect, request, session, url_for

from app.exceptions import AuthenticationRequiredError, UnauthorizedError
from app.extensions import get_db


def api_response(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def json_body():
    from app.exceptions import ValidationError

    values = request.get_json(silent=True)
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValidationError("The JSON request body must be an object.")
    return values


def current_user():
    user_id = session.get("user_id")
    if not user_id or not ObjectId.is_valid(user_id):
        return None
    user = get_db()["users"].find_one({"_id": ObjectId(user_id), "active": {"$ne": False}})
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                raise AuthenticationRequiredError("Authentication is required.")
            return redirect(url_for("web_auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if user["role"] not in roles:
                if request.path.startswith("/api/"):
                    raise UnauthorizedError("You do not have permission to access this resource.")
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def init_request_security(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_state_changes():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "CSRF token is missing or invalid.", "error_code": "CSRF_FAILED"}), 400
            abort(400, description="CSRF token is missing or invalid.")
        return None


def json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items() if key != "password_hash"}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value
