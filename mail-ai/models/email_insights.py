"""Lightweight, replaceable email summaries and local model evidence."""

import re
from typing import Any, List

import numpy as np


def _truncate_at_word(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    clipped = text[:max_chars - 3].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not clipped:
        clipped = text[:max_chars - 3].rstrip()
    return f"{clipped}..."


def summarize_email(subject: str, body: str, max_chars: int = 280) -> str:
    """Extract up to two leading sentences; use a short word window if unpunctuated.

    This is extractive: it copies text from the subject/body and never generates
    facts. When sentence boundaries are absent, the first 36 words are used.
    """
    source = "\n".join(part.strip() for part in (subject, body) if part and part.strip())
    if not source:
        return ""

    segments = [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+|[\r\n]+", source)
        if segment.strip()
    ]
    if len(segments) == 1:
        words = segments[0].split()
        if len(words) > 36:
            segments = [" ".join(words[:36])]
    else:
        segments = segments[:2]

    return _truncate_at_word(" ".join(segments), max_chars)


def top_linear_features(pipeline: Any, text: str, predicted_label: str, limit: int = 5) -> List[str]:
    """Return present TF-IDF terms with positive contribution to one class score.

    For Logistic Regression, each contribution is TF-IDF(term) multiplied by
    that class's learned coefficient. These local score contributions indicate
    association with the prediction, not causation or a guaranteed explanation.
    Unsupported pipelines return an empty list.
    """
    try:
        vectorizer = pipeline.named_steps["tfidf"]
        estimator = pipeline.named_steps["clf"]
        coefficients = np.asarray(estimator.coef_)
        classes = np.asarray(estimator.classes_)
        label_matches = np.flatnonzero(classes == predicted_label)
        if not len(label_matches):
            return []

        class_index = int(label_matches[0])
        if coefficients.shape[0] == 1:
            if len(classes) != 2:
                return []
            weights = coefficients[0] if class_index == 1 else -coefficients[0]
        elif coefficients.shape[0] == len(classes):
            weights = coefficients[class_index]
        else:
            return []

        features = vectorizer.transform([text]).tocsr()
        contributions = features.toarray()[0] * weights
        feature_names = vectorizer.get_feature_names_out()
        ranked_indices = np.argsort(contributions)[::-1]
        return [
            str(feature_names[index])
            for index in ranked_indices
            if contributions[index] > 0
        ][:limit]
    except (AttributeError, KeyError, TypeError, ValueError):
        return []
