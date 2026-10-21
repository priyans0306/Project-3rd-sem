"""
Mail AI — Intelligent Business Email Classification
Machine Learning Training Module (models/train_model.py)

Trains multi-target NLP pipelines for Category, Priority, and Risk Level.
Implements TF-IDF vectorization, Logistic Regression baseline, train-test splitting
without data leakage, comprehensive evaluation, and persistent model serialization.
"""

import os
import sys
import re
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# Configuration & Reproducibility
RANDOM_STATE = 42
TEST_SPLIT_SIZE = 0.20

VALID_CATEGORIES = {
    "Finance",
    "HR",
    "Operations",
    "Customer Support",
    "Sales",
    "Security",
    "General"
}

VALID_PRIORITIES = {"Low", "Medium", "High", "Urgent"}
VALID_RISK_LEVELS = {"Low", "Medium", "High"}


def clean_text(text: str) -> str:
    """
    Preprocess raw email text for NLP feature extraction:
    - Converts text to lowercase
    - Normalizes URLs and email addresses to generic tokens
    - Collapses consecutive whitespace
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", "url_token", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email_token", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def resolve_paths(
    data_arg: str = None,
    model_arg: str = None,
    evaluation_arg: str = None
) -> Tuple[str, str, str]:
    """
    Resolves filesystem paths for data, model output, and evaluation metrics
    supporting execution from workspace root or inside the mail-ai directory.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Locate dataset
    if data_arg:
        data_path = os.path.abspath(data_arg)
    else:
        candidates = [
            os.path.join(base_dir, "data", "training_emails.csv"),
            os.path.join(os.getcwd(), "data", "training_emails.csv"),
            os.path.join(os.getcwd(), "mail-ai", "data", "training_emails.csv")
        ]
        data_path = next((c for c in candidates if os.path.exists(c)), candidates[0])

    # Model and Evaluation Output Paths
    model_dir = os.path.join(base_dir, "models")
    model_path = os.path.abspath(model_arg) if model_arg else os.path.join(model_dir, "email_model.joblib")
    if evaluation_arg:
        eval_path = os.path.abspath(evaluation_arg)
    elif model_arg:
        eval_path = os.path.join(os.path.dirname(model_path), "evaluation_results.json")
    else:
        eval_path = os.path.join(model_dir, "evaluation_results.json")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(os.path.dirname(eval_path), exist_ok=True)

    return data_path, model_path, eval_path


def load_and_validate_data(data_path: str) -> pd.DataFrame:
    """
    Loads training_emails.csv and validates schema, missing values, and labels.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Dataset file not found at: '{data_path}'. "
            "Please ensure data/training_emails.csv exists before running training."
        )

    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV at '{data_path}': {str(e)}")

    required_cols = {"subject", "body", "category", "risk_level"}
    actual_cols = set(df.columns)
    missing_cols = required_cols - actual_cols
    if missing_cols:
        raise ValueError(f"Dataset is missing required columns: {missing_cols}")

    # Support 'priority' with 'urgency' fallback
    if "priority" not in df.columns and "urgency" in df.columns:
        df["priority"] = df["urgency"]
    elif "priority" not in df.columns:
        raise ValueError("Dataset must contain either 'priority' or 'urgency' column.")

    initial_count = len(df)
    if initial_count == 0:
        raise ValueError(f"Dataset at '{data_path}' contains 0 rows.")

    # Fill NaN and drop rows with empty subject AND body
    df["subject"] = df["subject"].fillna("").astype(str)
    df["body"] = df["body"].fillna("").astype(str)
    empty_email_mask = (
        (df["subject"].str.strip() == "") &
        (df["body"].str.strip() == "")
    )
    empty_email_count = int(empty_email_mask.sum())
    df = df[~empty_email_mask].copy()

    for column in ("category", "priority", "risk_level"):
        df[column] = df[column].fillna("").astype(str).str.strip()

    # Validate categorical labels
    valid_mask = (
        df["category"].isin(VALID_CATEGORIES) &
        df["priority"].isin(VALID_PRIORITIES) &
        df["risk_level"].isin(VALID_RISK_LEVELS)
    )
    invalid_label_count = int((~valid_mask).sum())
    if empty_email_count:
        print(f"[!] Warning: Dropped {empty_email_count} rows with no subject or body.")
    if invalid_label_count:
        print(f"[!] Warning: Dropped {invalid_label_count} rows with invalid categorical labels.")
    df = df[valid_mask].copy()

    if len(df) < 10:
        raise ValueError(f"Dataset has only {len(df)} valid rows; need at least 10 samples to train.")

    # Combine subject and body into single text feature
    df["combined_text"] = df["subject"] + " " + df["body"]
    df["cleaned_text"] = df["combined_text"].apply(clean_text)

    return df


def print_confusion_matrix(cm: np.ndarray, labels: list, title: str):
    """Prints a formatted ASCII confusion matrix to stdout."""
    print(f"\n--- Confusion Matrix: {title} ---")
    header = f"{'True \\ Pred':<18}" + "".join([f"{lbl[:10]:>12}" for lbl in labels])
    print(header)
    print("-" * len(header))
    for i, row_lbl in enumerate(labels):
        row_str = f"{row_lbl[:16]:<18}"
        for j in range(len(labels)):
            row_str += f"{cm[i, j]:>12}"
        print(row_str)


def evaluate_pipeline(
    pipeline: Pipeline,
    X_train: pd.Series,
    y_train: pd.Series,
    X_test: pd.Series,
    y_test: pd.Series,
    task_name: str
) -> Dict[str, Any]:
    """
    Evaluates a trained pipeline on both training and test splits.
    Returns metrics dictionary with reports and confusion matrix.
    """
    # Predictions
    y_train_pred = pipeline.predict(X_train)
    y_test_pred = pipeline.predict(X_test)

    # Classes in deterministic order
    classes = list(pipeline.classes_)

    # Metrics
    train_acc = float(accuracy_score(y_train, y_train_pred))
    test_acc = float(accuracy_score(y_test, y_test_pred))
    test_prec = float(precision_score(y_test, y_test_pred, average="weighted", zero_division=0))
    test_rec = float(recall_score(y_test, y_test_pred, average="weighted", zero_division=0))
    test_f1 = float(f1_score(y_test, y_test_pred, average="weighted", zero_division=0))

    report_dict = classification_report(y_test, y_test_pred, zero_division=0, output_dict=True)
    report_text = classification_report(y_test, y_test_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_test_pred, labels=classes)

    # Terminal output
    print(f"\n=======================================================")
    print(f" Target Evaluation: {task_name.upper()}")
    print(f"=======================================================")
    print(f"  Training Accuracy : {train_acc * 100:.2f}% (on {len(X_train)} samples)")
    print(f"  Testing Accuracy  : {test_acc * 100:.2f}% (on {len(X_test)} unseen samples)")
    print(f"  Testing Precision : {test_prec:.4f} (weighted)")
    print(f"  Testing Recall    : {test_rec:.4f} (weighted)")
    print(f"  Testing F1-Score  : {test_f1:.4f} (weighted)")
    print(f"\nDetailed Classification Report:\n{report_text}")
    print_confusion_matrix(cm, classes, task_name)

    return {
        "task": task_name,
        "classes": classes,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_accuracy": round(train_acc, 4),
        "test_accuracy": round(test_acc, 4),
        "precision_weighted": round(test_prec, 4),
        "recall_weighted": round(test_rec, 4),
        "f1_weighted": round(test_f1, 4),
        "classification_report": report_dict,
        "confusion_matrix": cm.tolist()
    }


def train_models(
    data_path: str = None,
    model_output_path: str = None,
    evaluation_output_path: str = None
) -> Dict[str, Any]:
    """
    End-to-end training routine:
    1. Validates and loads dataset
    2. Performs train/test split with stratification
    3. Builds TF-IDF + Logistic Regression pipelines (no leakage)
    4. Evaluates all targets thoroughly
    5. Saves serialized model bundle and evaluation report
    """
    resolved_data, resolved_model, resolved_eval = resolve_paths(
        data_path,
        model_output_path,
        evaluation_output_path
    )

    print("=======================================================")
    print(" Mail AI — Machine Learning Model Training")
    print(f" Source Data : {resolved_data}")
    print(f" Output Model: {resolved_model}")
    print(f" Eval Report : {resolved_eval}")
    print(f" Random State: {RANDOM_STATE} | Test Split: {int(TEST_SPLIT_SIZE * 100)}%")
    print("=======================================================")

    # 1. Load and validate data
    df = load_and_validate_data(resolved_data)
    print(f"[OK] Valid dataset loaded: {len(df)} total business email records.")

    X = df["cleaned_text"]
    y_category = df["category"]
    y_priority = df["priority"]
    y_risk = df["risk_level"]

    # 2. Train-Test Split (stratified on category to ensure even representation)
    (
        X_train, X_test,
        y_cat_tr, y_cat_te,
        y_prio_tr, y_prio_te,
        y_risk_tr, y_risk_te
    ) = train_test_split(
        X, y_category, y_priority, y_risk,
        test_size=TEST_SPLIT_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_category
    )

    print(f"[OK] Data split into {len(X_train)} training samples and {len(X_test)} testing samples.")
    print(f"     (Zero data leakage: vectorizers are fitted strictly on X_train)")

    # 3. Model Pipeline 1: Email Category Classifier (7 Classes)
    print("\n[*] Training Category Pipeline (TF-IDF + Balanced Logistic Regression)...")
    cat_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
            stop_words="english"
        )),
        ("clf", LogisticRegression(
            C=4.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE
        ))
    ])
    cat_pipeline.fit(X_train, y_cat_tr)
    cat_eval = evaluate_pipeline(cat_pipeline, X_train, y_cat_tr, X_test, y_cat_te, "Email Category")

    # 4. Model Pipeline 2: Email Priority Classifier (4 Levels)
    print("\n[*] Training Priority Pipeline (TF-IDF + Balanced Logistic Regression)...")
    prio_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=4000,
            sublinear_tf=True,
            stop_words="english"
        )),
        ("clf", LogisticRegression(
            C=3.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE
        ))
    ])
    prio_pipeline.fit(X_train, y_prio_tr)
    prio_eval = evaluate_pipeline(prio_pipeline, X_train, y_prio_tr, X_test, y_prio_te, "Email Priority")

    # 5. Model Pipeline 3: Email Risk Level Classifier (3 Levels)
    print("\n[*] Training Risk Level Pipeline (TF-IDF + Balanced Logistic Regression)...")
    risk_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=4000,
            sublinear_tf=True,
            stop_words="english"
        )),
        ("clf", LogisticRegression(
            C=3.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE
        ))
    ])
    risk_pipeline.fit(X_train, y_risk_tr)
    risk_eval = evaluate_pipeline(risk_pipeline, X_train, y_risk_tr, X_test, y_risk_te, "Email Risk Level")

    # 6. Assemble Serialized Bundle
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    model_bundle = {
        "category_pipeline": cat_pipeline,
        "priority_pipeline": prio_pipeline,
        "urgency_pipeline": prio_pipeline,  # Backward compatibility alias
        "risk_pipeline": risk_pipeline,
        "categories": list(cat_pipeline.classes_),
        "priorities": list(prio_pipeline.classes_),
        "urgencies": list(prio_pipeline.classes_),
        "risk_levels": list(risk_pipeline.classes_),
        "metrics": {
            "category_accuracy": cat_eval["test_accuracy"],
            "category_f1": cat_eval["f1_weighted"],
            "priority_accuracy": prio_eval["test_accuracy"],
            "priority_f1": prio_eval["f1_weighted"],
            "urgency_accuracy": prio_eval["test_accuracy"],
            "urgency_f1": prio_eval["f1_weighted"],
            "risk_accuracy": risk_eval["test_accuracy"],
            "risk_f1": risk_eval["f1_weighted"],
            "train_sample_count": len(X_train),
            "test_sample_count": len(X_test),
            "sample_count": len(df),
            "trained_at": timestamp_str
        },
        "evaluation": {
            "category": cat_eval,
            "priority": prio_eval,
            "risk_level": risk_eval
        }
    }

    # 7. Save model bundle to joblib file
    joblib.dump(model_bundle, resolved_model)
    print(f"\n[OK] Model bundle successfully saved to: {resolved_model}")

    # 8. Save persistent evaluation report as JSON
    eval_report = {
        "project": "Mail AI — Intelligent Business Email Classification",
        "trained_at": timestamp_str,
        "random_state": RANDOM_STATE,
        "total_dataset_rows": len(df),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "evaluation_summary": {
            "category": {
                "test_accuracy": cat_eval["test_accuracy"],
                "precision_weighted": cat_eval["precision_weighted"],
                "recall_weighted": cat_eval["recall_weighted"],
                "f1_weighted": cat_eval["f1_weighted"]
            },
            "priority": {
                "test_accuracy": prio_eval["test_accuracy"],
                "precision_weighted": prio_eval["precision_weighted"],
                "recall_weighted": prio_eval["recall_weighted"],
                "f1_weighted": prio_eval["f1_weighted"]
            },
            "risk_level": {
                "test_accuracy": risk_eval["test_accuracy"],
                "precision_weighted": risk_eval["precision_weighted"],
                "recall_weighted": risk_eval["recall_weighted"],
                "f1_weighted": risk_eval["f1_weighted"]
            }
        },
        "detailed_metrics": {
            "category": cat_eval,
            "priority": prio_eval,
            "risk_level": risk_eval
        }
    }

    with open(resolved_eval, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)
    print(f"[OK] Evaluation results saved for later review: {resolved_eval}\n")

    return model_bundle


if __name__ == "__main__":
    cli_data_path = sys.argv[1] if len(sys.argv) > 1 else None
    cli_model_path = sys.argv[2] if len(sys.argv) > 2 else None
    cli_eval_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        train_models(
            data_path=cli_data_path,
            model_output_path=cli_model_path,
            evaluation_output_path=cli_eval_path
        )
    except Exception as exc:
        print(f"\n[ERROR] Training failed: {exc}", file=sys.stderr)
        sys.exit(1)
