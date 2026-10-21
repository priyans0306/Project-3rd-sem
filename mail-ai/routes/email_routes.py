"""
Email Routes for Mail AI
Intelligent Business Email Classification
REST API endpoints for email classification, inbox management, and actions.
"""

import logging
import re
import sqlite3

from flask import Blueprint, request, jsonify
from services.email_service import EmailService
from services.classification_service import ClassificationService

email_bp = Blueprint("emails", __name__, url_prefix="/api/emails")
email_service = EmailService()
classification_service = ClassificationService()
logger = logging.getLogger(__name__)

MAX_SUBJECT_LENGTH = 500
MAX_BODY_LENGTH = 50000
MAX_ADDRESS_LENGTH = 320
MAX_PAGE_SIZE = 100
MAX_FILTER_LENGTH = 200
MAX_BATCH_ITEMS = 100


def _error_response(error):
    logger.error("Email API request failed (%s)", type(error).__name__)
    if isinstance(error, (FileNotFoundError, RuntimeError)):
        return jsonify({
            "success": False,
            "error": "The email classification model is unavailable. Train or restore the model artifacts."
        }), 503
    if isinstance(error, sqlite3.Error):
        return jsonify({
            "success": False,
            "error": "The database is temporarily unavailable."
        }), 503
    if isinstance(error, (TypeError, ValueError)):
        return jsonify({"success": False, "error": str(error)}), 400
    return jsonify({
        "success": False,
        "error": "The request could not be completed."
    }), 500


def _validate_email_data(data):
    if not isinstance(data, dict):
        return None, (jsonify({"success": False, "error": "Request body must be a JSON object."}), 400)

    values = {
        "subject": data.get("subject", ""),
        "body": data.get("body", ""),
        "sender": data.get("sender", ""),
        "recipient": data.get("recipient", "support@mailai.enterprise.com")
    }
    limits = {
        "subject": MAX_SUBJECT_LENGTH,
        "body": MAX_BODY_LENGTH,
        "sender": MAX_ADDRESS_LENGTH,
        "recipient": MAX_ADDRESS_LENGTH
    }
    for field, value in values.items():
        if not isinstance(value, str):
            return None, (jsonify({
                "success": False,
                "error": f"Field '{field}' must be a string."
            }), 400)
        values[field] = value.strip()
        if len(values[field]) > limits[field]:
            return None, (jsonify({
                "success": False,
                "error": f"Field '{field}' must be at most {limits[field]} characters."
            }), 400)
        if field in {"sender", "recipient"} and values[field] and not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+", values[field]
        ):
            return None, (jsonify({
                "success": False,
                "error": f"Field '{field}' must be a valid email address."
            }), 400)

    if not values["subject"] and not values["body"]:
        return None, (jsonify({
            "success": False,
            "error": "At least 'subject' or 'body' must contain text."
        }), 400)
    return values, None


def _validated_email_payload():
    if not request.is_json:
        return None, (jsonify({"success": False, "error": "Content-Type must be application/json."}), 415)
    return _validate_email_data(request.get_json(silent=True))


def _validated_filters():
    names = ("category", "priority", "urgency", "risk_level", "status", "search")
    filters = {}
    for name in names:
        value = request.args.get(name, "")
        if len(value) > MAX_FILTER_LENGTH:
            return None, (jsonify({
                "success": False,
                "error": f"Query field '{name}' must be at most {MAX_FILTER_LENGTH} characters."
            }), 400)
        filters[name] = value.strip() or None
    return filters, None


def _parse_pagination():
    if len(request.args.get("limit", "50")) > 10 or len(request.args.get("offset", "0")) > 10:
        return None, (jsonify({
            "success": False,
            "error": "'limit' and 'offset' values are too long."
        }), 400)
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return None, (jsonify({
            "success": False,
            "error": "'limit' and 'offset' must be integers."
        }), 400)
    if limit < 1 or limit > MAX_PAGE_SIZE or offset < 0:
        return None, (jsonify({
            "success": False,
            "error": f"'limit' must be between 1 and {MAX_PAGE_SIZE}, and 'offset' must be non-negative."
        }), 400)
    return (limit, offset), None


@email_bp.route("/classify", methods=["POST"])
def classify_email_endpoint():
    """
    POST /api/emails/classify
    Classifies and stores an email in the inbox.
    Body JSON: { "subject": "...", "body": "...", "sender": "..." }
    """
    payload, error = _validated_email_payload()
    if error:
        return error

    try:
        saved_email = email_service.process_and_save_email(
            subject=payload["subject"],
            body=payload["body"],
            sender=payload["sender"],
            recipient=payload["recipient"]
        )
        return jsonify({
            "success": True,
            "data": saved_email,
            "message": "Email classified and saved successfully."
        }), 201
    except Exception as exc:
        return _error_response(exc)


@email_bp.route("", methods=["POST"])
def create_email_endpoint():
    """
    POST /api/emails
    Classifies and saves an incoming email to the SQLite database.
    """
    payload, error = _validated_email_payload()
    if error:
        return error

    try:
        saved_email = email_service.process_and_save_email(
            subject=payload["subject"],
            body=payload["body"],
            sender=payload["sender"],
            recipient=payload["recipient"]
        )
        return jsonify({
            "success": True,
            "data": saved_email,
            "message": "Email classified and saved successfully."
        }), 201
    except Exception as exc:
        return _error_response(exc)


@email_bp.route("", methods=["GET"])
@email_bp.route("/", methods=["GET"])
def get_emails_endpoint():
    """
    GET /api/emails
    Retrieves filtered emails from the database.
    Query Params: category, priority, urgency, risk_level, status, search, limit, offset
    """
    pagination, error = _parse_pagination()
    if error:
        return error
    limit, offset = pagination
    filters, error = _validated_filters()
    if error:
        return error
    category = filters["category"]
    priority = filters["priority"]
    urgency = filters["urgency"]
    risk_level = filters["risk_level"]
    status = filters["status"]
    search = filters["search"]
    try:
        emails = email_service.get_inbox_emails(
            category=category,
            priority=priority,
            urgency=urgency,
            risk_level=risk_level,
            status=status,
            search=search,
            limit=limit,
            offset=offset
        )
        total = email_service.count_inbox_emails(
            category=category,
            priority=priority,
            urgency=urgency,
            risk_level=risk_level,
            status=status,
            search=search
        )
        return jsonify({
            "success": True,
            "count": len(emails),
            "total": total,
            "pagination": {"limit": limit, "offset": offset},
            "data": emails
        }), 200
    except Exception as exc:
        return _error_response(exc)


@email_bp.route("/<int:email_id>", methods=["GET"])
def get_single_email_endpoint(email_id: int):
    """
    GET /api/emails/<email_id>
    Fetches full details of a specific email.
    """
    try:
        email = email_service.get_email_details(email_id)
        if not email:
            return jsonify({
                "success": False,
                "error": f"Email with ID {email_id} not found."
            }), 404

        # Add probabilities and indicators for the details modal
        full_analysis = classification_service.classify_email(
            email["subject"],
            email["body"],
            email["sender"]
        )
        email["category_probabilities"] = full_analysis.get("category_probabilities", {})
        email["urgency_probabilities"] = full_analysis.get("urgency_probabilities", {})
        email["risk_probabilities"] = full_analysis.get("risk_probabilities", {})
        email["risk_indicators"] = full_analysis.get("risk_indicators", [])
        email["risk_indicators_disclaimer"] = full_analysis.get("risk_indicators_disclaimer", "")
        email["summary"] = full_analysis.get("summary", "")
        email["category_evidence"] = full_analysis.get("category_evidence", [])
        email["priority_evidence"] = full_analysis.get("priority_evidence", [])
        email["action_description"] = full_analysis.get("action_description", "")

        return jsonify({
            "success": True,
            "data": email
        }), 200
    except Exception as exc:
        return _error_response(exc)


@email_bp.route("/<int:email_id>/status", methods=["PATCH"])
def update_email_status_endpoint(email_id: int):
    """
    PATCH /api/emails/<email_id>/status
    Body JSON: { "status": "Resolved" }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
    new_status = data.get("status")

    if not isinstance(new_status, str) or not new_status:
        return jsonify({
            "success": False,
            "error": "Field 'status' is required."
        }), 400

    try:
        updated = email_service.update_status(email_id, new_status)
        if not updated:
            return jsonify({
                "success": False,
                "error": f"Email with ID {email_id} not found."
            }), 404

        return jsonify({
            "success": True,
            "message": f"Status updated to '{new_status}' successfully."
        }), 200
    except Exception as exc:
        return _error_response(exc)


@email_bp.route("/<int:email_id>", methods=["DELETE"])
def delete_email_endpoint(email_id: int):
    """
    DELETE /api/emails/<email_id>
    """
    try:
        deleted = email_service.remove_email(email_id)
        if not deleted:
            return jsonify({
                "success": False,
                "error": f"Email with ID {email_id} not found."
            }), 404

        return jsonify({
            "success": True,
            "message": f"Email {email_id} deleted successfully."
        }), 200
    except Exception as exc:
        return _error_response(exc)


@email_bp.route("/batch-classify", methods=["POST"])
def batch_classify_endpoint():
    """
    POST /api/emails/batch-classify
    Body JSON: { "emails": [ { "subject": "...", "body": "..." } ] }
    """
    if not request.is_json:
        return jsonify({"success": False, "error": "Content-Type must be application/json."}), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
    emails_list = data.get("emails", [])

    if not isinstance(emails_list, list) or not emails_list:
        return jsonify({
            "success": False,
            "error": "'emails' must be a non-empty array of email objects."
        }), 400
    if len(emails_list) > MAX_BATCH_ITEMS:
        return jsonify({
            "success": False,
            "error": f"'emails' must contain no more than {MAX_BATCH_ITEMS} items."
        }), 400

    validated_emails = []
    for item in emails_list:
        email_data, error = _validate_email_data(item)
        if error:
            return error
        validated_emails.append(email_data)

    try:
        results = classification_service.classify_batch(validated_emails)
        return jsonify({
            "success": True,
            "count": len(results),
            "data": results
        }), 200
    except Exception as exc:
        return _error_response(exc)
