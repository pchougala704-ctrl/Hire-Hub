from flask import Flask, jsonify, render_template, request
from pathlib import Path

from app.config import Config
from app.exceptions import HireHubError
from app.extensions import init_database
from app.utils import init_request_security


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    if isinstance(config_object, dict):
        app.config.update(config_object)
    else:
        if config_object is not Config:
            app.config.from_object(config_object)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY in the environment before starting HireHub.")
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    if not upload_folder.is_absolute():
        upload_folder = Path(app.root_path).parent / upload_folder
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_folder.resolve())
    init_database(app)
    init_request_security(app)

    from app.routes.api import api_bp
    from app.routes.api import routes as api_routes
    from app.routes.web import auth_bp, web_bp
    from app.routes.web import auth_routes, main_routes

    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(HireHubError)
    def handle_hirehub_error(error):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "message": str(error),
                "error_code": error.code,
            }), error.status_code
        return render_template("errors/error.html", message=str(error)), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Resource not found.", "error_code": "NOT_FOUND"}), 404
        return render_template("errors/error.html", message="The page could not be found."), 404

    @app.errorhandler(403)
    def handle_forbidden(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "You do not have permission to access this resource.", "error_code": "UNAUTHORIZED"}), 403
        return render_template("errors/error.html", message="You do not have permission to access this resource."), 403

    @app.errorhandler(413)
    def handle_too_large(error):
        limit_mb = max(1, app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024))
        message = f"The uploaded file exceeds the {limit_mb} MB size limit."
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": message, "error_code": "FILE_TOO_LARGE"}), 413
        return render_template("errors/error.html", message=message), 413

    return app
