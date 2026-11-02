"""Tests for the SQLite email and classification store."""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from database import db


class TestEmailDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = db.DB_FILE
        db.set_database_path(os.path.join(self.temp_dir.name, "mail-ai.sqlite"))
        db.init_db()

    def tearDown(self):
        db.set_database_path(self.original_path)
        self.temp_dir.cleanup()

    @staticmethod
    def email_record(subject="Test subject", **extra):
        record = {
            "subject": subject,
            "body": "Test body",
            "sender": "sender@example.com",
            "category": "Operations",
            "priority": "Urgent",
            "risk_level": "Low",
            "confidence": 0.87,
            "priority_confidence": 0.82,
            "risk_confidence": 0.94,
            "model_version": "test-model-v1",
            "key_phrases": ["test", "body"]
        }
        record.update(extra)
        return record

    def test_initialization_creates_tables_indexes_and_foreign_key(self):
        conn = db.get_db_connection()
        try:
            tables = {
                row["name"] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = ?",
                    ("table",)
                )
            }
            self.assertIn("emails", tables)
            self.assertIn("classifications", tables)

            email_columns = {row["name"] for row in conn.execute("PRAGMA table_info(emails)")}
            classification_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(classifications)")
            }
            self.assertTrue({"id", "subject", "body", "sender", "received_at", "created_at"}.issubset(email_columns))
            self.assertTrue({
                "id", "email_id", "category", "priority", "risk_level", "confidence",
                "model_version", "classified_at"
            }.issubset(classification_columns))

            foreign_keys = conn.execute("PRAGMA foreign_key_list(classifications)").fetchall()
            self.assertTrue(any(
                row["table"] == "emails" and row["from"] == "email_id" and row["on_delete"] == "CASCADE"
                for row in foreign_keys
            ))
            indexes = {
                row["name"] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = ?",
                    ("index",)
                )
            }
            self.assertIn("idx_classifications_category", indexes)
            self.assertIn("idx_classifications_priority", indexes)
            self.assertIn("idx_classifications_risk", indexes)
        finally:
            conn.close()

    def test_insert_retrieve_latest_and_classification_history(self):
        email_id = db.insert_email(self.email_record(received_at="2026-10-20T10:00:00-05:00"))

        email = db.get_email_by_id(email_id)
        self.assertEqual(email["subject"], "Test subject")
        self.assertEqual(email["category"], "Operations")
        self.assertEqual(email["confidence"], 0.87)
        self.assertEqual(email["received_at"], "2026-10-20T15:00:00.000Z")
        self.assertTrue(email["created_at"].endswith("Z"))
        self.assertEqual(email["key_phrases"], ["test", "body"])

        original_history = db.get_classification_history(email_id)
        duplicate_id = db.add_classification(email_id, self.email_record(confidence=0.65))
        self.assertEqual(duplicate_id, original_history[0]["id"])
        self.assertEqual(len(db.get_classification_history(email_id)), 1)

        db.add_classification(email_id, self.email_record(
            confidence=0.93,
            priority="High",
            model_version="test-model-v2"
        ))
        history = db.get_classification_history(email_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(db.get_email_by_id(email_id)["model_version"], "test-model-v2")
        self.assertEqual(db.get_email_by_id(email_id)["confidence"], 0.93)

    def test_missing_demo_data_is_added_once_without_removing_existing_emails(self):
        existing_id = db.insert_email(self.email_record(subject="Existing inbox email"))
        preset = self.email_record(
            subject="Category sample email",
            sender="sample@example.com",
            model_version="sample-model-v1"
        )

        self.assertEqual(db.insert_missing_demo_data([preset]), 1)
        self.assertEqual(db.insert_missing_demo_data([preset]), 0)
        self.assertEqual(db.count_emails(), 2)
        self.assertIsNotNone(db.get_email_by_id(existing_id))
        self.assertEqual(
            db.get_emails(search="Category sample email")[0]["sender"],
            "sample@example.com"
        )

    def test_filter_search_pagination_count_and_delete(self):
        first_id = db.insert_email(self.email_record(subject="Unique needle alpha"))
        second_id = db.insert_email(self.email_record(
            subject="Unique needle beta",
            priority="Low",
            model_version="test-model-v2"
        ))
        db.insert_email(self.email_record(
            subject="Different message",
            category="Finance",
            model_version="test-model-v3"
        ))

        page = db.get_emails(category="Operations", search="Unique needle", limit=1, offset=0)
        self.assertEqual(len(page), 1)
        self.assertEqual(db.count_emails(category="Operations", search="Unique needle"), 2)
        self.assertEqual(db.count_emails(priority="Urgent", risk_level="Low"), 2)
        self.assertEqual(db.count_emails(search="' OR 1=1 --"), 0)

        self.assertTrue(db.delete_email(first_id))
        self.assertFalse(db.delete_email(first_id))
        self.assertEqual(db.get_classification_history(first_id), [])
        self.assertEqual(db.count_emails(category="Operations", search="Unique needle"), 1)
        self.assertIsNotNone(db.get_email_by_id(second_id))

    def test_email_and_classification_insert_roll_back_together(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_email(self.email_record(confidence=2.0))
        self.assertEqual(db.count_emails(), 0)

    def test_demo_replacement_rolls_back_when_classification_insert_fails(self):
        email_id = db.insert_email(self.email_record(subject="Preserve during reset failure"))
        with patch("database.db._insert_classification_row", side_effect=sqlite3.IntegrityError("insert failed")):
            with self.assertRaises(sqlite3.IntegrityError):
                db.replace_demo_data([self.email_record(subject="Replacement")])
        self.assertEqual(db.count_emails(), 1)
        self.assertIsNotNone(db.get_email_by_id(email_id))

    def test_init_migrates_legacy_records_once(self):
        legacy_path = os.path.join(self.temp_dir.name, "legacy.sqlite")
        legacy = sqlite3.connect(legacy_path)
        legacy.execute("""
            CREATE TABLE emails (
                id INTEGER PRIMARY KEY,
                sender TEXT NOT NULL,
                recipient TEXT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT NOT NULL,
                category_confidence REAL NOT NULL,
                priority TEXT NOT NULL,
                priority_confidence REAL NOT NULL,
                urgency TEXT NOT NULL,
                urgency_confidence REAL NOT NULL,
                risk_level TEXT NOT NULL,
                risk_confidence REAL NOT NULL,
                suggested_action TEXT NOT NULL,
                routed_department TEXT NOT NULL,
                sla TEXT,
                status TEXT,
                key_phrases TEXT,
                created_at TEXT
            )
        """)
        legacy.execute("""
            INSERT INTO emails VALUES (
                7, 'legacy@example.com', 'support@example.com', 'Legacy subject', 'Legacy body',
                'Finance', 0.8, 'Low', 0.7, 'Low', 0.7, 'Low', 0.9,
                'PROCESS', 'Finance', 'Normal', 'Unread', '[]', '2026-01-02 03:04:05'
            )
        """)
        legacy.commit()
        legacy.close()

        db.set_database_path(legacy_path)
        db.init_db()
        db.init_db()

        email = db.get_email_by_id(7)
        self.assertEqual(email["subject"], "Legacy subject")
        self.assertEqual(email["category"], "Finance")
        self.assertEqual(len(db.get_classification_history(7)), 1)
        self.assertEqual(email["received_at"], "2026-01-02T03:04:05.000Z")


if __name__ == "__main__":
    unittest.main()
