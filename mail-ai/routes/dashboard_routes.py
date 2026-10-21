"""
Dashboard Routes for Mail AI
Intelligent Business Email Classification
Provides analytics, Chart.js datasets, KPI metrics, and demo presets.
"""

import logging
import sqlite3

from flask import Blueprint, jsonify
from services.email_service import EmailService
from services.demo_data import DEMO_PRESETS

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")
email_service = EmailService()
logger = logging.getLogger(__name__)


def _dashboard_error(error):
    logger.error("Dashboard API request failed (%s)", type(error).__name__)
    if isinstance(error, sqlite3.Error):
        return jsonify({"success": False, "error": "The database is temporarily unavailable."}), 503
    if isinstance(error, (FileNotFoundError, RuntimeError)):
        return jsonify({
            "success": False,
            "error": "The email classification model is unavailable. Train or restore the model artifacts."
        }), 503
    return jsonify({"success": False, "error": "The request could not be completed."}), 500

@dashboard_bp.route("/stats", methods=["GET"])
def get_dashboard_stats_endpoint():
    """
    GET /api/dashboard/stats
    Returns aggregate stats for KPI metric cards and Chart.js visualizations.
    """
    try:
        analytics = email_service.get_analytics_summary()
        return jsonify({
            "success": True,
            "data": analytics
        }), 200
    except Exception as exc:
        return _dashboard_error(exc)


@dashboard_bp.route("/presets", methods=["GET"])
def get_presets_endpoint():
    """
    GET /api/dashboard/presets
    Returns quick preset emails for the live classifier form demo.
    """
    return jsonify({
        "success": True,
        "data": DEMO_PRESETS
    }), 200


@dashboard_bp.route("/reset-demo", methods=["POST"])
def reset_demo_database_endpoint():
    """
    POST /api/dashboard/reset-demo
    Clears the emails table and re-seeds it with default sample records.
    """
    try:
        email_service.reset_demo_inbox()

        analytics = email_service.get_analytics_summary()
        return jsonify({
            "success": True,
            "message": "Database reset to initial demo state successfully.",
            "data": analytics
        }), 200
    except Exception as exc:
        return _dashboard_error(exc)
