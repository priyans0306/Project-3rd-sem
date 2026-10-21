"""
Dataset Validator for Mail AI
Verifies that training_emails.csv conforms to the required schema,
contains no null/empty values, and only uses allowable categorical labels.
"""

import os
import sys
import pandas as pd

REQUIRED_COLUMNS = ["subject", "body", "category", "priority", "risk_level"]

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


def validate_csv(csv_path: str) -> bool:
    print(f"[*] Validating dataset: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"[FAIL] File not found: {csv_path}")
        return False

    df = pd.read_csv(csv_path)

    # 1. Check Columns
    actual_cols = list(df.columns)
    if actual_cols != REQUIRED_COLUMNS:
        print(f"[FAIL] Column mismatch! Expected: {REQUIRED_COLUMNS}, got: {actual_cols}")
        return False
    print(f"[OK] Header columns match expected schema: {actual_cols}")

    # 2. Check Row Count
    total_rows = len(df)
    if total_rows == 0:
        print("[FAIL] Dataset is empty!")
        return False
    print(f"[OK] Total rows loaded: {total_rows}")

    # 3. Check Missing / Null values
    null_counts = df.isnull().sum()
    if null_counts.any():
        print(f"[FAIL] Null values found:\n{null_counts[null_counts > 0]}")
        return False
    print("[OK] No null or missing values found across any columns.")

    # 4. Check for empty strings in text
    empty_subjects = (df["subject"].str.strip() == "").sum()
    empty_bodies = (df["body"].str.strip() == "").sum()
    if empty_subjects > 0 or empty_bodies > 0:
        print(f"[FAIL] Found {empty_subjects} empty subjects and {empty_bodies} empty bodies.")
        return False
    print("[OK] All subjects and bodies contain non-empty text.")

    # 5. Validate Categories
    invalid_cats = set(df["category"].unique()) - VALID_CATEGORIES
    if invalid_cats:
        print(f"[FAIL] Found invalid categories: {invalid_cats}")
        return False
    print(f"[OK] Categories valid. Found all {len(VALID_CATEGORIES)} expected categories:")
    for cat, count in df["category"].value_counts().items():
        print(f"     - {cat:20s}: {count} samples")

    # 6. Validate Priorities
    invalid_priorities = set(df["priority"].unique()) - VALID_PRIORITIES
    if invalid_priorities:
        print(f"[FAIL] Found invalid priorities: {invalid_priorities}")
        return False
    print(f"[OK] Priorities valid. Found all {len(VALID_PRIORITIES)} expected priorities:")
    for prio, count in df["priority"].value_counts().items():
        print(f"     - {prio:20s}: {count} samples")

    # 7. Validate Risk Levels
    invalid_risks = set(df["risk_level"].unique()) - VALID_RISK_LEVELS
    if invalid_risks:
        print(f"[FAIL] Found invalid risk levels: {invalid_risks}")
        return False
    print(f"[OK] Risk levels valid. Found all {len(VALID_RISK_LEVELS)} expected risk levels:")
    for rsk, count in df["risk_level"].value_counts().items():
        print(f"     - {rsk:20s}: {count} samples")

    print("\n[SUCCESS] Dataset passed 100% of validation checks!\n")
    return True


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "training_emails.csv"
    )
    success = validate_csv(csv_file)
    sys.exit(0 if success else 1)
