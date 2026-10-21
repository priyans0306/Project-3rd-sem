"""Coordinate input validation and model-backed email classification."""

import math
from numbers import Real
from typing import Any, Dict, List, Optional, Protocol

from models.email_classifier import EmailClassifier

VALID_CATEGORIES = {
    "Customer Support",
    "Finance",
    "General",
    "HR",
    "Operations",
    "Sales",
    "Security"
}
VALID_PRIORITIES = {"Low", "Medium", "High", "Urgent"}
VALID_RISK_LEVELS = {"Low", "Medium", "High"}


class ClassificationError(RuntimeError):
    """Base error for failed inference or invalid model predictions."""


class ModelUnavailableError(ClassificationError):
    """Raised when the trained model artifacts cannot be loaded."""


class InvalidPredictionError(ClassificationError):
    """Raised when a model returns a result outside the service contract."""


class PredictionModel(Protocol):
    def classify(self, subject: str, body: str, sender: str = "") -> Dict[str, Any]:
        """Return model predictions for the supplied email."""


_classifier_instance: Optional[EmailClassifier] = None


def get_classifier() -> EmailClassifier:
    """Return the shared model instance, loading artifacts only when needed."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = EmailClassifier()
    return _classifier_instance


class ClassificationService:
    """Validate requests and predictions around a replaceable ML model."""

    def __init__(self, classifier: Optional[PredictionModel] = None):
        self._classifier = classifier

    @property
    def classifier(self) -> PredictionModel:
        if self._classifier is None:
            return get_classifier()
        return self._classifier

    @staticmethod
    def _validate_email(subject: str, body: str, sender: str) -> tuple[str, str, str]:
        if not isinstance(subject, str) or not isinstance(body, str):
            raise TypeError("Email subject and body must be strings.")
        if not isinstance(sender, str):
            raise TypeError("Email sender must be a string.")

        subject = subject.strip()
        body = body.strip()
        sender = sender.strip()
        if not subject and not body:
            raise ValueError("Email must have either a non-empty subject or body.")
        return subject, body, sender or "unknown@domain.com"

    @staticmethod
    def _validated_result(prediction: Any) -> Dict[str, Any]:
        if not isinstance(prediction, dict):
            raise InvalidPredictionError("The classifier returned an invalid result.")

        category = prediction.get("category")
        priority = prediction.get("priority") or prediction.get("urgency")
        risk_level = prediction.get("risk_level")
        confidence_scores = {
            "category_confidence": prediction.get("category_confidence"),
            "priority_confidence": prediction.get("priority_confidence"),
            "risk_confidence": prediction.get("risk_confidence")
        }
        if confidence_scores["category_confidence"] is None:
            confidence_scores["category_confidence"] = prediction.get("confidence")
        if confidence_scores["priority_confidence"] is None:
            confidence_scores["priority_confidence"] = prediction.get("urgency_confidence")

        if not isinstance(category, str) or category.strip() not in VALID_CATEGORIES:
            raise InvalidPredictionError("The classifier returned an invalid email category.")
        if not isinstance(priority, str) or priority.strip() not in VALID_PRIORITIES:
            raise InvalidPredictionError("The classifier returned an invalid email priority.")
        if not isinstance(risk_level, str) or risk_level.strip() not in VALID_RISK_LEVELS:
            raise InvalidPredictionError("The classifier returned an invalid email risk level.")
        for field, score in confidence_scores.items():
            if isinstance(score, bool) or not isinstance(score, Real):
                raise InvalidPredictionError(f"The classifier returned an invalid {field} score.")
            score = float(score)
            if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                raise InvalidPredictionError(f"The classifier returned an invalid {field} score.")
            confidence_scores[field] = score

        result = dict(prediction)
        result.update({
            "category": category.strip(),
            "priority": priority.strip(),
            "urgency": priority.strip(),
            "risk_level": risk_level.strip(),
            **confidence_scores,
            "confidence": confidence_scores["category_confidence"]
        })
        return result

    def classify_email(self, subject: str, body: str, sender: str = "") -> Dict[str, Any]:
        """Validate an email, classify it, and return a consistent result."""
        subject, body, sender = self._validate_email(subject, body, sender)

        try:
            classifier = self.classifier
        except (FileNotFoundError, OSError, RuntimeError, ImportError) as exc:
            raise ModelUnavailableError(
                "The email classification model is unavailable. Train or restore the model artifacts."
            ) from exc

        try:
            prediction = classifier.classify(subject, body, sender)
        except Exception as exc:
            raise ClassificationError("Email classification failed.") from exc

        result = self._validated_result(prediction)
        result.update({"subject": subject, "body": body, "sender": sender})
        return result

    def classify_batch(self, emails: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Classify a batch of email records using the same validation path."""
        if not isinstance(emails, list):
            raise TypeError("Emails must be provided as a list.")

        results = []
        for item in emails:
            if not isinstance(item, dict):
                raise TypeError("Each email in the batch must be an object.")
            results.append(self.classify_email(
                item.get("subject", ""),
                item.get("body", ""),
                item.get("sender", "")
            ))
        return results

    def get_model_metrics(self) -> Dict[str, Any]:
        """Return metrics from the active trained model."""
        try:
            return self.classifier.get_metrics()
        except (FileNotFoundError, OSError) as exc:
            raise ModelUnavailableError(
                "The email classification model is unavailable. Train or restore the model artifacts."
            ) from exc
        except Exception as exc:
            raise ClassificationError("Model metrics are unavailable.") from exc
