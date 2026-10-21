"""Unit tests for model-independent classification service behavior."""

import unittest
from unittest.mock import patch

from services.classification_service import (
    ClassificationError,
    ClassificationService,
    InvalidPredictionError,
    ModelUnavailableError
)


class FakeClassifier:
    def __init__(self, prediction=None, error=None):
        self.prediction = prediction or {
            "category": "Operations",
            "priority": "Urgent",
            "risk_level": "High",
            "confidence": 0.91,
            "category_probabilities": {"Operations": 0.91},
            "priority_confidence": 0.84,
            "risk_confidence": 0.73
        }
        self.error = error

    def classify(self, subject, body, sender=""):
        if self.error:
            raise self.error
        return dict(self.prediction)

    def get_metrics(self):
        return {"category_accuracy": 0.8}


class TestClassificationService(unittest.TestCase):
    def test_success_returns_normalized_prediction_and_email(self):
        service = ClassificationService(FakeClassifier())

        result = service.classify_email("  Conveyor stopped ", "  Line 2 is blocked.  ")

        self.assertEqual(result["category"], "Operations")
        self.assertEqual(result["priority"], "Urgent")
        self.assertEqual(result["urgency"], "Urgent")
        self.assertEqual(result["risk_level"], "High")
        self.assertEqual(result["confidence"], 0.91)
        self.assertEqual(result["category_confidence"], 0.91)
        self.assertEqual(result["priority_confidence"], 0.84)
        self.assertEqual(result["risk_confidence"], 0.73)
        self.assertEqual(result["subject"], "Conveyor stopped")
        self.assertEqual(result["body"], "Line 2 is blocked.")
        self.assertEqual(result["sender"], "unknown@domain.com")
        self.assertEqual(result["category_probabilities"], {"Operations": 0.91})

    def test_invalid_email_input_is_rejected_before_inference(self):
        model = FakeClassifier()
        service = ClassificationService(model)

        with self.assertRaisesRegex(ValueError, "non-empty subject or body"):
            service.classify_email("  ", "\n")
        with self.assertRaisesRegex(TypeError, "subject and body must be strings"):
            service.classify_email(None, "body")
        with self.assertRaisesRegex(TypeError, "sender must be a string"):
            service.classify_email("subject", "body", sender=123)

    def test_invalid_model_predictions_are_rejected(self):
        invalid_predictions = [
            {"category": "Unknown", "priority": "Urgent", "risk_level": "High", "confidence": 0.9, "priority_confidence": 0.8, "risk_confidence": 0.7},
            {"category": "Operations", "priority": "Immediate", "risk_level": "High", "confidence": 0.9, "priority_confidence": 0.8, "risk_confidence": 0.7},
            {"category": "Operations", "priority": "Urgent", "risk_level": "Critical", "confidence": 0.9, "priority_confidence": 0.8, "risk_confidence": 0.7},
            {"category": "Operations", "priority": "Urgent", "risk_level": "High", "confidence": 1.1, "priority_confidence": 0.8, "risk_confidence": 0.7},
            {"category": "Operations", "priority": "Urgent", "risk_level": "High", "confidence": 0.9, "priority_confidence": float("nan"), "risk_confidence": 0.7}
        ]
        for prediction in invalid_predictions:
            with self.subTest(prediction=prediction):
                service = ClassificationService(FakeClassifier(prediction=prediction))
                with self.assertRaises(InvalidPredictionError):
                    service.classify_email("subject", "body")

    def test_missing_artifact_is_a_controlled_unavailable_error(self):
        service = ClassificationService()
        for error in (FileNotFoundError("missing model"), RuntimeError("invalid model bundle")):
            with self.subTest(error=error):
                with patch(
                    "services.classification_service.get_classifier",
                    side_effect=error
                ):
                    with self.assertRaisesRegex(ModelUnavailableError, "model is unavailable"):
                        service.classify_email("subject", "body")

    def test_inference_failure_does_not_create_prediction(self):
        service = ClassificationService(FakeClassifier(error=RuntimeError("model failure")))
        with self.assertRaisesRegex(ClassificationError, "classification failed"):
            service.classify_email("subject", "body")


if __name__ == "__main__":
    unittest.main()