"""
Mail AI — Intelligent Business Email Classification
Main Flask Application Entry Point
"""

import os
import sys

# Ensure current directory is on python sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, jsonify
from database import db as database
from routes.email_routes import email_bp
from routes.dashboard_routes import dashboard_bp
from services.classification_service import get_classifier
from services.email_service import EmailService


def create_app(config: dict = None) -> Flask:
    """Application factory for Mail AI."""
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static")
    )
    app.config.from_mapping(
        DATABASE=database.DB_FILE,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        APP_ENV=os.environ.get("APP_ENV", "development").strip().lower(),
        DEBUG=False
    )
    if config:
        app.config.update(config)
    if app.config["APP_ENV"] == "production":
        app.config["DEBUG"] = False
    database.set_database_path(app.config["DATABASE"])

    try:
        database.init_db()
        email_service = EmailService()
        if database.count_emails() == 0:
            email_service.reset_demo_inbox()
        else:
            email_service.ensure_demo_inbox_samples()
            email_service.refresh_legacy_predictions()
    except Exception as exc:
        app.logger.error("Application initialization failed (%s)", type(exc).__name__)

    # Register Blueprints
    app.register_blueprint(email_bp)
    app.register_blueprint(dashboard_bp)

    @app.route("/")
    def index():
        """Serves the main single-page Mail AI dashboard and classifier UI."""
        return render_template("index.html")

    @app.route("/health")
    @app.route("/api/health")
    def health_check():
        """Report app and dependency availability without exposing internals."""
        database_available = database.database_available()
        try:
            get_classifier()
            model_available = True
        except Exception as exc:
            app.logger.error("Model availability check failed (%s)", type(exc).__name__)
            model_available = False

        healthy = database_available and model_available
        return jsonify({
            "success": healthy,
            "status": "healthy" if healthy else "degraded",
            "app": "Mail AI — Intelligent Business Email Classification",
            "version": "1.0.0",
            "ml_engine": "Scikit-Learn TF-IDF + LogisticRegression",
            "model_available": model_available,
            "database_available": database_available
        }), 200 if healthy else 503

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "The requested resource was not found."
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Unhandled request error (%s)", type(error).__name__)
        return jsonify({
            "success": False,
            "error": "The request could not be completed."
        }), 500

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "success": False,
            "error": "The HTTP method is not allowed for this endpoint."
        }), 405

    @app.errorhandler(413)
    def request_too_large(error):
        return jsonify({
            "success": False,
            "error": "The request body is too large."
        }), 413

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n========================================================")
    print(f" Mail AI Server Running on http://127.0.0.1:{port}")
    print(f" College Project: Intelligent Business Email Classification")
    print(f"========================================================\n")
    is_production = app.config["APP_ENV"] == "production"
    debug = not is_production and os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, debug=debug)
