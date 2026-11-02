"""
Automated Test Suite for Mail AI
Verifies Models, Services, Database, and REST API Endpoints.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from database import db as database
from models.email_classifier import EmailClassifier, classify_email
from routes import dashboard_routes
from routes import email_routes
from services.email_service import EmailService
from services.demo_data import DEMO_PRESETS


class TestMailAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test Flask client and database."""
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.classifier = EmailClassifier()

    def test_01_health_endpoint(self):
        """Test the JSON dependency health endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("Scikit-Learn", data["ml_engine"])
        self.assertTrue(data["model_available"])
        self.assertTrue(data["database_available"])

    def test_02_index_html_renders(self):
        """Test GET / serves HTML page."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mail AI", response.data)
        self.assertIn(b"chart.umd.min.js", response.data)

    def test_03_classifier_customer_support(self):
        """Test machine learning classification for support & outage."""
        res = self.classifier.classify(
            subject="CRITICAL: Production checkout service returning HTTP 500 internal errors",
            body="Customer checkout transactions on the web storefront are failing with 500 internal server errors. Payment gateway webhooks appear stuck."
        )
        self.assertEqual(res["category"], "Customer Support")
        self.assertIn(res["priority"], ["High", "Urgent"])
        self.assertIn("key_phrases", res)
        self.assertGreater(res["category_confidence"], 0.3)

    def test_04_classifier_phishing_security(self):
        """Test machine learning classification for security phishing alert."""
        res = self.classifier.classify(
            subject="CRITICAL: Corporate Mailbox Quota Exceeded - Verify Password Now",
            body="Your corporate Office 365 storage has exceeded 99%. To prevent immediate account deactivation, verify your credentials at http://portal-auth-check.xyz/login within 2 hours."
        )
        self.assertEqual(res["category"], "Security")
        self.assertEqual(res["priority"], "Urgent")
        self.assertEqual(res["risk_level"], "High")
        self.assertIn("QUARANTINE", res["suggested_action"])

    def test_classifier_insights_handle_punctuation_free_email(self):
        result = self.classifier.classify(
            subject="Urgent database outage",
            body="checkout is stopped customers cannot place orders"
        )
        self.assertTrue(result["summary"])
        self.assertLessEqual(len(result["summary"]), 280)
        self.assertIn("database outage", result["summary"].lower())
        self.assertIsInstance(result["category_evidence"], list)
        self.assertIsInstance(result["priority_evidence"], list)
        self.assertIn("do not prove malicious intent", result["risk_indicators_disclaimer"])

    def test_04a_compact_classifier_normal_email(self):
        result = classify_email(
            subject="Discrepancy in monthly consulting invoice INV-2026-402",
            body="Please issue a corrected invoice for the hours that exceed our signed agreement."
        )
        self.assertEqual(result["category"], "Finance")
        self.assertEqual(set(result), {"category", "priority", "risk_level", "confidence"})
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_04b_compact_classifier_urgent_email(self):
        result = classify_email(
            subject="CRITICAL: Production checkout service returning HTTP 500 errors",
            body="Customer checkout transactions are failing and payment gateway webhooks appear stuck."
        )
        self.assertEqual(result["category"], "Customer Support")
        self.assertIn(result["priority"], ["High", "Urgent"])

    def test_04c_compact_classifier_suspicious_email(self):
        result = classify_email(
            subject="Corporate Mailbox Quota Exceeded - Verify Password Now",
            body="Verify your credentials at http://portal-auth-check.xyz/login to prevent account deactivation."
        )
        self.assertEqual(result["category"], "Security")
        self.assertEqual(result["risk_level"], "High")

    def test_04d_classifier_rejects_empty_and_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "non-empty subject or body"):
            classify_email("  ", "\n")
        with self.assertRaisesRegex(TypeError, "must be strings"):
            classify_email(None, "Email body")

    def test_04e_classifier_reports_missing_model_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_model = os.path.join(temp_dir, "missing-model.joblib")
            with self.assertRaisesRegex(FileNotFoundError, "models/train_model.py"):
                EmailClassifier(model_path=missing_model)

    def test_05_api_classify_endpoint(self):
        """Test POST /api/emails/classify."""
        payload = {
            "subject": "Enterprise sales inquiry: Inbound email triage for 2,500 support agents",
            "body": "We receive over 60,000 customer emails monthly and want to schedule an executive demo of Mail AI.",
            "sender": "sales-inquiry@megacorp.com"
        }
        response = self.client.post(
            "/api/emails/classify",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["category"], "Sales")
        self.assertIn("priority", data["data"])
        self.assertIn("id", data["data"])
        self.assertEqual(self.client.delete(f"/api/emails/{data['data']['id']}").status_code, 200)

    def test_06_api_create_and_fetch_email(self):
        """Test POST /api/emails and GET /api/emails/<id>."""
        payload = {
            "sender": "testuser@enterprise.org",
            "subject": "Discrepancy in monthly consulting invoice INV-2026-402",
            "body": "Hi Accounts, we noticed invoice INV-2026-402 bills for 65 hours when our agreement was 40 hours. Please issue a corrected invoice."
        }
        create_res = self.client.post(
            "/api/emails",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(create_res.status_code, 201)
        created_data = create_res.get_json()
        self.assertTrue(created_data["success"])
        email_id = created_data["data"]["id"]

        # Fetch single email
        get_res = self.client.get(f"/api/emails/{email_id}")
        self.assertEqual(get_res.status_code, 200)
        email_data = get_res.get_json()["data"]
        self.assertEqual(email_data["category"], "Finance")
        self.assertEqual(email_data["sender"], "testuser@enterprise.org")

        # Update status
        patch_res = self.client.patch(
            f"/api/emails/{email_id}/status",
            data=json.dumps({"status": "Resolved"}),
            content_type="application/json"
        )
        self.assertEqual(patch_res.status_code, 200)

        # Delete email
        del_res = self.client.delete(f"/api/emails/{email_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_07_dashboard_stats_endpoint(self):
        """Test GET /api/dashboard/stats."""
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("total_emails", data["data"])
        self.assertIn("category_counts", data["data"])
        self.assertIn("priority_counts", data["data"])
        self.assertIn("model_metrics", data["data"])

    def test_08_dashboard_presets_endpoint(self):
        """Test GET /api/dashboard/presets."""
        response = self.client.get("/api/dashboard/presets")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["data"]), 15)

        category_counts = {}
        for item in data["data"]:
            category = item["title"].split(":", 1)[0].strip()
            category_counts[category] = category_counts.get(category, 0) + 1

        self.assertGreaterEqual(len(category_counts), 7)
        self.assertGreaterEqual(min(category_counts.values()), 3)
        self.assertGreater(len(set(category_counts.values())), 1)


class TestBackendEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_database_path = database.DB_FILE
        cls.app = create_app({
            "TESTING": True,
            "DATABASE": os.path.join(cls.temp_dir.name, "api-tests.sqlite")
        })
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        database.set_database_path(cls.original_database_path)
        cls.temp_dir.cleanup()

    def _create_email(self, subject, body="Please review this message."):
        response = self.client.post("/api/emails/classify", json={
            "subject": subject,
            "body": body,
            "sender": "api-test@example.com"
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["data"]

    def test_classify_endpoint_saves_actual_prediction(self):
        email = self._create_email(
            "API classification persistence check invoice 2026",
            "Please correct the duplicate invoice charge and send the updated statement."
        )
        self.assertIsInstance(email["category"], str)
        self.assertIsInstance(email["priority"], str)
        self.assertIsInstance(email["risk_level"], str)
        self.assertGreaterEqual(email["confidence"], 0)
        self.assertLessEqual(email["confidence"], 1)
        self.assertTrue(email["summary"])
        self.assertIn("category_evidence", email)
        self.assertIn("priority_evidence", email)
        fetched = self.client.get(f"/api/emails/{email['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertIn("category_probabilities", fetched.get_json()["data"])
        self.assertEqual(self.client.delete(f"/api/emails/{email['id']}").status_code, 200)

    def test_email_list_search_filters_and_pagination(self):
        first = self._create_email("Pagination marker alpha", "first matching record")
        second = self._create_email("Pagination marker beta", "second matching record")
        try:
            response = self.client.get("/api/emails?search=Pagination%20marker&limit=1&offset=0")
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["total"], 2)
            self.assertEqual(data["pagination"], {"limit": 1, "offset": 0})

            category = data["data"][0]["category"]
            filtered = self.client.get(f"/api/emails?category={category}&search=Pagination%20marker")
            self.assertEqual(filtered.status_code, 200)
            filtered_data = filtered.get_json()
            self.assertGreater(filtered_data["total"], 0)
            self.assertTrue(all(email["category"] == category for email in filtered_data["data"]))
        finally:
            self.client.delete(f"/api/emails/{first['id']}")
            self.client.delete(f"/api/emails/{second['id']}")

    def test_api_validates_payload_and_pagination(self):
        self.assertEqual(self.client.post("/api/emails/classify", json={}).status_code, 400)
        self.assertEqual(
            self.client.post("/api/emails/classify", json={"subject": 5, "body": "text"}).status_code,
            400
        )
        self.assertEqual(
            self.client.post("/api/emails/classify", json={"subject": "x" * 501, "body": "text"}).status_code,
            400
        )
        self.assertEqual(self.client.get("/api/emails?limit=not-a-number").status_code, 400)
        self.assertEqual(self.client.get("/api/emails?limit=101").status_code, 400)
        self.assertEqual(self.client.get("/api/emails/").status_code, 200)
        self.assertEqual(self.client.post("/api/emails/classify", data="{}", content_type="text/plain").status_code, 415)

    def test_api_rejects_long_filters_and_invalid_batches(self):
        self.assertEqual(
            self.client.get("/api/emails", query_string={"search": "x" * 201}).status_code,
            400
        )
        self.assertEqual(self.client.post("/api/emails/batch-classify", json=[]).status_code, 400)
        self.assertEqual(
            self.client.post("/api/emails/batch-classify", json={"emails": [{"subject": 42}]}).status_code,
            400
        )
        self.assertEqual(
            self.client.post("/api/emails/batch-classify", json={"emails": [{"subject": "a", "sender": "bad"}]}).status_code,
            400
        )
        self.assertEqual(
            self.client.post("/api/emails/batch-classify", json={"emails": [{}] * 101}).status_code,
            400
        )

    def test_api_rejects_oversized_request_body_with_json(self):
        response = self.client.post(
            "/api/emails/classify",
            data="x" * (2 * 1024 * 1024 + 1),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"], "The request body is too large.")

    def test_classification_failure_response_does_not_expose_exception(self):
        logger = email_routes.logger
        with patch.object(
            email_routes.email_service,
            "process_and_save_email",
            side_effect=RuntimeError("sensitive email body text")
        ), patch.object(logger, "error") as log_error:
            response = self.client.post("/api/emails/classify", json={
                "subject": "Valid subject",
                "body": "Valid body"
            })
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("sensitive email body text", response.get_data(as_text=True))
        self.assertNotIn("sensitive email body text", str(log_error.call_args))

    def test_invalid_status_error_does_not_reflect_payload(self):
        email = self._create_email("Status reflection validation", "Safe test message.")
        payload = "<img src=x onerror=alert(1)>"
        response = self.client.patch(
            f"/api/emails/{email['id']}/status",
            json={"status": payload}
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(payload, response.get_data(as_text=True))
        self.client.delete(f"/api/emails/{email['id']}")

    def test_dashboard_stats_include_required_breakdowns(self):
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.get_json()["data"]
        self.assertIn("total_emails", stats)
        self.assertIn("classified_emails", stats)
        self.assertEqual(stats["classified_emails"], sum(stats["category_counts"].values()))
        self.assertEqual(stats["urgent_emails"], stats["priority_counts"].get("Urgent", 0))
        self.assertIn("category_counts", stats)
        self.assertIn("priority_counts", stats)
        self.assertIn("risk_counts", stats)
        self.assertEqual(stats["high_risk_emails"], stats["risk_counts"].get("High", 0))

    def test_demo_reset_stores_actual_model_predictions(self):
        startup_rows = database.get_emails(limit=100)
        self.assertEqual(len(startup_rows), len(DEMO_PRESETS))
        startup_preset = DEMO_PRESETS[0]
        startup_expected = EmailClassifier().classify(
            startup_preset["subject"],
            startup_preset["body"],
            startup_preset["sender"]
        )
        startup_saved = next(row for row in startup_rows if row["subject"] == startup_preset["subject"])
        self.assertEqual(startup_saved["category"], startup_expected["category"])
        self.assertEqual(startup_saved["priority"], startup_expected["priority"])
        self.assertEqual(startup_saved["risk_level"], startup_expected["risk_level"])
        self.assertEqual(startup_saved["confidence"], startup_expected["category_confidence"])

        response = self.client.post("/api/dashboard/reset-demo")
        self.assertEqual(response.status_code, 200)
        rows = database.get_emails(limit=100)
        self.assertEqual(len(rows), len(DEMO_PRESETS))

        preset = DEMO_PRESETS[0]
        expected = EmailClassifier().classify(preset["subject"], preset["body"], preset["sender"])
        saved = next(row for row in rows if row["subject"] == preset["subject"])
        self.assertEqual(saved["category"], expected["category"])
        self.assertEqual(saved["priority"], expected["priority"])
        self.assertEqual(saved["risk_level"], expected["risk_level"])
        self.assertEqual(saved["confidence"], expected["category_confidence"])

    def test_legacy_prediction_is_refreshed_and_history_is_preserved(self):
        email_id = database.insert_email({
            "subject": "Legacy migration verification",
            "body": "Please review the old stored label against the active classifier.",
            "sender": "legacy@example.org",
            "category": "General",
            "priority": "Low",
            "risk_level": "Low",
            "confidence": 0.5,
            "model_version": "legacy-migration"
        })

        refreshed = EmailService().refresh_legacy_predictions()

        history = database.get_classification_history(email_id)
        latest = database.get_email_by_id(email_id)
        self.assertGreaterEqual(refreshed, 1)
        self.assertEqual(len(history), 2)
        self.assertNotEqual(latest["model_version"], "legacy-migration")
        self.assertEqual(latest["category"], EmailClassifier().classify(
            latest["subject"], latest["body"], latest["sender"]
        )["category"])
        database.delete_email(email_id)

    def test_dashboard_stats_handles_missing_model(self):
        with patch.object(
            dashboard_routes.email_service,
            "get_analytics_summary",
            side_effect=FileNotFoundError("private model path")
        ):
            response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private model path", response.get_data(as_text=True))

    def test_health_reports_unavailable_database(self):
        original_database_path = database.DB_FILE
        try:
            unavailable_app = create_app({
                "TESTING": True,
                "DATABASE": self.temp_dir.name
            })
            response = unavailable_app.test_client().get("/api/health")
        finally:
            database.set_database_path(original_database_path)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["database_available"])

    def test_health_reports_unavailable_model(self):
        with patch("app.get_classifier", side_effect=FileNotFoundError("private artifact path")):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["model_available"])
        self.assertNotIn("private artifact path", response.get_data(as_text=True))

    def test_production_configuration_forces_debug_off(self):
        previous_path = database.DB_FILE
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                production_app = create_app({
                    "TESTING": True,
                    "APP_ENV": "production",
                    "DEBUG": True,
                    "DATABASE": os.path.join(temp_dir, "production.sqlite")
                })
                self.assertFalse(production_app.config["DEBUG"])
            finally:
                database.set_database_path(previous_path)


if __name__ == "__main__":
    unittest.main()
