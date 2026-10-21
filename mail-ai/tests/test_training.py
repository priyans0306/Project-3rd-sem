"""Pytest coverage for dataset validation, training, and model reloads."""

import json

import pandas as pd
import pytest

from models.email_classifier import EmailClassifier
from models.train_model import load_and_validate_data, resolve_paths, train_models


@pytest.fixture(scope="module")
def trained_bundle(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("trained-model")
    model_path = output_dir / "email_model.joblib"
    evaluation_path = output_dir / "evaluation_results.json"
    dataset_path = "data/training_emails.csv"
    bundle = train_models(
        data_path=dataset_path,
        model_output_path=str(model_path),
        evaluation_output_path=str(evaluation_path)
    )
    return bundle, model_path, evaluation_path


def test_dataset_validation_drops_blank_and_invalid_rows(tmp_path):
    rows = [
        {
            "subject": f"Business subject {index}",
            "body": "A meaningful email body",
            "category": "Finance",
            "priority": "Medium",
            "risk_level": "Low"
        }
        for index in range(12)
    ]
    rows.extend([
        {"subject": "  ", "body": "", "category": "Finance", "priority": "Low", "risk_level": "Low"},
        {"subject": "Bad label", "body": "Text", "category": "Unknown", "priority": "Low", "risk_level": "Low"}
    ])
    csv_path = tmp_path / "validation.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    result = load_and_validate_data(str(csv_path))

    assert len(result) == 12
    assert result["cleaned_text"].str.len().gt(0).all()
    assert set(result["category"]) == {"Finance"}


def test_missing_or_invalid_dataset_fails_without_fallback(tmp_path):
    missing_path = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError, match="Dataset file not found"):
        load_and_validate_data(str(missing_path))

    invalid_path = tmp_path / "invalid.csv"
    pd.DataFrame([{"subject": "Only a subject"}]).to_csv(invalid_path, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_and_validate_data(str(invalid_path))


def test_training_saves_three_pipelines_and_evaluation_to_temp_paths(trained_bundle):
    bundle, model_path, evaluation_path = trained_bundle

    assert model_path.is_file()
    assert evaluation_path.is_file()
    assert {"category_pipeline", "priority_pipeline", "risk_pipeline"}.issubset(bundle)
    assert set(bundle["evaluation"]) == {"category", "priority", "risk_level"}

    report = json.loads(evaluation_path.read_text(encoding="utf-8"))
    assert report["train_rows"] + report["test_rows"] == report["total_dataset_rows"]
    for target in ("category", "priority", "risk_level"):
        metrics = report["evaluation_summary"][target]
        for name in ("test_accuracy", "precision_weighted", "recall_weighted", "f1_weighted"):
            assert 0.0 <= metrics[name] <= 1.0
        assert "confusion_matrix" in report["detailed_metrics"][target]


def test_custom_model_path_keeps_default_evaluation_local(tmp_path):
    _, model_path, evaluation_path = resolve_paths(
        "data/training_emails.csv",
        str(tmp_path / "model.joblib")
    )
    assert model_path == str(tmp_path / "model.joblib")
    assert evaluation_path.startswith(str(tmp_path))


def test_loaded_model_predicts_category_priority_and_risk(trained_bundle):
    _, model_path, _ = trained_bundle
    classifier = EmailClassifier(model_path=str(model_path))
    result = classifier.classify(
        "CRITICAL: Production database outage",
        "Checkout is down and customers cannot place orders."
    )

    assert result["category"] in classifier.bundle["categories"]
    assert result["priority"] in classifier.bundle["priorities"]
    assert result["risk_level"] in classifier.bundle["risk_levels"]
    for score in (result["confidence"], result["priority_confidence"], result["risk_confidence"]):
        assert 0.0 <= score <= 1.0
    assert result["summary"]
