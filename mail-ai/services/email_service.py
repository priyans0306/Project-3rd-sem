"""
Email Service for Mail AI
Intelligent Business Email Classification
Manages business logic for email classification, ingestion, status updates, and retrieval.
"""

from typing import Dict, Any, List, Optional
from services.classification_service import ClassificationService
from database.db import (
    insert_email,
    get_emails,
    get_email_by_id,
    update_email_status,
    delete_email,
    count_emails,
    get_dashboard_metrics,
    replace_demo_data,
    insert_missing_demo_data,
    get_legacy_or_unclassified_emails,
    add_classification
)
from services.demo_data import DEMO_PRESETS


class EmailService:
    def __init__(self):
        self.classification_service = ClassificationService()

    def process_and_save_email(
        self,
        subject: str,
        body: str,
        sender: str = "",
        recipient: str = "support@mailai.enterprise.com"
    ) -> Dict[str, Any]:
        """
        Classifies email content, extracts intelligence, and stores in SQLite.
        """
        prediction = self.classification_service.classify_email(subject, body, sender)
        email_record = self._email_record(subject, body, sender, recipient, prediction)

        email_id = insert_email(email_record)
        saved_email = get_email_by_id(email_id)
        saved_email.update(self._prediction_details(prediction))
        return saved_email

    @staticmethod
    def _email_record(subject, body, sender, recipient, prediction):
        priority = prediction["priority"]
        return {
            "sender": sender or "customer@client.com",
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "category": prediction["category"],
            "category_confidence": prediction["category_confidence"],
            "confidence": prediction["category_confidence"],
            "priority": priority,
            "priority_confidence": prediction["priority_confidence"],
            "risk_level": prediction["risk_level"],
            "risk_confidence": prediction["risk_confidence"],
            "model_version": "active-model",
            "suggested_action": prediction["suggested_action"],
            "routed_department": prediction["routed_department"],
            "sla": prediction["sla"],
            "status": "Escalated" if prediction["risk_level"] == "High" else "Unread",
            "key_phrases": prediction["key_phrases"]
        }

    @staticmethod
    def _prediction_details(prediction):
        return {
            "category_probabilities": prediction["category_probabilities"],
            "priority_probabilities": prediction["priority_probabilities"],
            "urgency_probabilities": prediction["urgency_probabilities"],
            "risk_probabilities": prediction["risk_probabilities"],
            "risk_indicators": prediction["risk_indicators"],
            "risk_indicators_disclaimer": prediction["risk_indicators_disclaimer"],
            "summary": prediction["summary"],
            "category_evidence": prediction["category_evidence"],
            "priority_evidence": prediction["priority_evidence"],
            "action_description": prediction["action_description"]
        }

    def _classified_demo_records(self):
        records = []
        for preset in DEMO_PRESETS:
            prediction = self.classification_service.classify_email(
                preset["subject"],
                preset["body"],
                preset["sender"]
            )
            records.append(self._email_record(
                preset["subject"],
                preset["body"],
                preset["sender"],
                "support@mailai.enterprise.com",
                prediction
            ))
        return records

    def reset_demo_inbox(self):
        """Classify built-in demo text with the active model, then store atomically."""
        records = self._classified_demo_records()
        replace_demo_data(records)

    def ensure_demo_inbox_samples(self) -> int:
        """Add any missing built-in sample emails without changing existing inbox rows."""
        return insert_missing_demo_data(self._classified_demo_records())

    def refresh_legacy_predictions(self) -> int:
        """Replace known static migration labels with current model outputs."""
        metrics = self.classification_service.get_model_metrics()
        model_version = str(metrics.get("trained_at") or "current-model")
        pending = get_legacy_or_unclassified_emails(model_version)
        for email in pending:
            prediction = self.classification_service.classify_email(
                email["subject"],
                email["body"],
                email["sender"]
            )
            add_classification(email["id"], {
                "category": prediction["category"],
                "priority": prediction["priority"],
                "risk_level": prediction["risk_level"],
                "confidence": prediction["category_confidence"],
                "priority_confidence": prediction["priority_confidence"],
                "risk_confidence": prediction["risk_confidence"],
                "model_version": model_version
            })
        return len(pending)

    def get_inbox_emails(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        urgency: Optional[str] = None,
        risk_level: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves email list with applied filters."""
        return get_emails(
            category=category,
            priority=priority,
            urgency=urgency,
            risk_level=risk_level,
            status=status,
            search=search,
            limit=limit,
            offset=offset
        )

    def get_email_details(self, email_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves detailed email record."""
        return get_email_by_id(email_id)

    def count_inbox_emails(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        urgency: Optional[str] = None,
        risk_level: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """Count records matching inbox filters, independent of pagination."""
        return count_emails(
            category=category,
            priority=priority,
            urgency=urgency,
            risk_level=risk_level,
            status=status,
            search=search
        )

    def update_status(self, email_id: int, status: str) -> bool:
        """Updates the processing status of an email."""
        valid_statuses = {"Unread", "Read", "Resolved", "Escalated", "Archived"}
        if status not in valid_statuses:
            raise ValueError(
                "Invalid email status. Choose Unread, Read, Resolved, Escalated, or Archived."
            )
        return update_email_status(email_id, status)

    def remove_email(self, email_id: int) -> bool:
        """Deletes an email by ID."""
        return delete_email(email_id)

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Combines database aggregates and model metrics."""
        db_stats = get_dashboard_metrics()
        model_metrics = self.classification_service.get_model_metrics()

        return {
            **db_stats,
            "model_metrics": model_metrics
        }
