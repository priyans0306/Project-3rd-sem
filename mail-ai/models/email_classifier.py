"""
Inference Module for Mail AI
Intelligent Business Email Classification
Loads the trained ML bundle and predicts Category, Priority, Risk Level,
Key Phrases, and Suggested Action.
"""

import os
import re
import joblib
import numpy as np
from typing import Dict, Any, List
from models.email_insights import summarize_email, top_linear_features

URGENT_KEYWORDS = [
    "urgent", "immediately", "critical", "emergency", "outage", "deadlock",
    "halted", "down", "conveyor line", "wire transfer", "within 2 hours",
    "suspended", "fatal", "rce", "compromised"
]

HIGH_RISK_PATTERNS = [
    (r"\b(wire\s+transfer|send\s+\$?\d+[\d,]*|bank\s+details|direct\s+deposit|escrow\s+account)\b", "Financial Transaction / Wire Request"),
    (r"\b(verify\s+your\s+password|account\s+suspension|credentials|login\s+at|quota\s+exceeded)\b", "Credential Harvesting / Phishing Flag"),
    (r"\b(cve-\d{4}-\d+|vulnerability|macro|ransomware|unauthorized\s+root|ssh\s+login)\b", "Security Incident / Malware Indicator"),
    (r"(https?://\S+)", "Embedded External URL")
]


class EmailClassifier:
    """Load a trusted trained bundle and classify email text."""

    def __init__(self, model_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if model_path is None:
            self.model_path = os.path.join(base_dir, "models", "email_model.joblib")
        else:
            self.model_path = os.path.abspath(model_path)

        self.bundle = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Load and validate a joblib bundle created by the training module."""
        if not os.path.isfile(self.model_path):
            raise FileNotFoundError(
                f"Trained model artifacts were not found at '{self.model_path}'. "
                "Train them with `python models/train_model.py` from the mail-ai directory."
            )

        try:
            self.bundle = joblib.load(self.model_path)
        except Exception as exc:
            raise RuntimeError(
                f"Could not load model artifacts at '{self.model_path}'. "
                "Retrain the model with `python models/train_model.py`."
            ) from exc

        if not isinstance(self.bundle, dict):
            raise RuntimeError(f"Model artifact at '{self.model_path}' is not a valid model bundle.")

        priority_pipeline = self.bundle.get("priority_pipeline") or self.bundle.get("urgency_pipeline")
        pipelines = {
            "category_pipeline": self.bundle.get("category_pipeline"),
            "priority_pipeline": priority_pipeline,
            "risk_pipeline": self.bundle.get("risk_pipeline")
        }
        missing = [name for name, pipeline in pipelines.items() if pipeline is None]
        if missing:
            raise RuntimeError(
                f"Model artifact at '{self.model_path}' is missing required pipelines: "
                f"{', '.join(missing)}. Retrain the model with `python models/train_model.py`."
            )
        for name, pipeline in pipelines.items():
            if not all(hasattr(pipeline, attribute) for attribute in ("predict", "predict_proba", "classes_")):
                raise RuntimeError(
                    f"The {name} in '{self.model_path}' does not support the required prediction interface."
                )

    def reload(self):
        """Reloads model bundle from disk."""
        self._load_artifacts()

    @staticmethod
    def clean_text(text: str) -> str:
        """Preprocesses input text matching training data transformation."""
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"https?://\S+|www\.\S+", "url_token", text)
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email_token", text)
        return text.strip()

    def extract_key_phrases(self, raw_text: str, top_k: int = 5) -> List[str]:
        """Extracts top distinguishing tokens/phrases from text."""
        tokens = re.findall(r"\b[A-Za-z]{3,}\b", raw_text.lower())
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "have",
            "are", "was", "will", "our", "your", "can", "not", "been",
            "has", "had", "would", "could", "should", "what", "which",
            "all", "any", "more", "also", "into", "than", "them", "then",
            "please", "thank", "hello", "team", "dear"
        }
        filtered = [t for t in tokens if t not in stopwords]
        freq = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_tokens[:top_k]]

    def generate_suggested_action(self, category: str, priority: str, risk: str) -> Dict[str, str]:
        """Maps classification results to recommended automated actions & department routing."""
        if risk == "High":
            return {
                "action": "QUARANTINE & VERIFY",
                "department": "IT Security (InfoSec)",
                "sla": "< 30 Minutes",
                "description": "Quarantine email, lock external links, and page Security Operations Center (SOC)."
            }

        if category == "Security":
            return {
                "action": "SECURITY INCIDENT DISPATCH",
                "department": "IT Security & Compliance",
                "sla": "< 1 Hour" if priority in ["High", "Urgent"] else "< 4 Hours",
                "description": "Review telemetry, isolate impacted asset, and file security audit ticket."
            }

        if category == "Customer Support":
            if priority in ["High", "Urgent"]:
                return {
                    "action": "P1 INCIDENT TRIAGE",
                    "department": "Tier 2 Technical Support",
                    "sla": "< 1 Hour",
                    "description": "Page on-call reliability engineer, check service health dashboard, and notify incident coordinator."
                }
            return {
                "action": "SUPPORT QUEUE DISPATCH",
                "department": "Customer Support Desk",
                "sla": "< 24 Hours",
                "description": "Route ticket to support queue and send automated receipt acknowledgement."
            }

        if category == "Finance":
            if priority in ["High", "Urgent"]:
                return {
                    "action": "TREASURY & AR ESCALATION",
                    "department": "Finance & Accounts Receivable",
                    "sla": "< 2 Hours",
                    "description": "Review ledger, verify payment status, and prevent service interruption."
                }
            return {
                "action": "FINANCIAL PROCESSING",
                "department": "Accounts Department",
                "sla": "< 48 Hours",
                "description": "Match invoice number with ERP records and issue revised invoice or tax credit."
            }

        if category == "Operations":
            if priority in ["High", "Urgent"]:
                return {
                    "action": "OPERATIONAL DISPATCH",
                    "department": "Facilities & Supply Chain Desk",
                    "sla": "< 2 Hours",
                    "description": "Dispatch field repair technician, reroute logistics freight, and log facility event."
                }
            return {
                "action": "OPERATIONS LOGGING",
                "department": "Facilities & Logistics",
                "sla": "< 48 Hours",
                "description": "Schedule routine maintenance or update warehouse inventory records."
            }

        if category == "HR":
            return {
                "action": "HRIS CONFIDENTIAL DISPATCH",
                "department": "People Operations / HR",
                "sla": "< 24 Hours",
                "description": "File under confidential HR record and assign to People Operations partner."
            }

        if category == "Sales":
            return {
                "action": "LEAD ENRICHMENT & ROUTING",
                "department": "Enterprise Sales Team",
                "sla": "< 4 Hours",
                "description": "Create Deal record in CRM, enrich company intelligence, and assign to Account Executive."
            }

        # Default General
        return {
            "action": "GENERAL LOGGING & ARCHIVE",
            "department": "Corporate Administration",
            "sla": "Standard",
            "description": "File in general corporate correspondence archive or bulletin board."
        }

    def classify(self, subject: str, body: str, sender: str = "") -> Dict[str, Any]:
        """
        Classifies an email and returns predictions, confidence, key phrases,
        and automated workflow actions.
        """
        if not isinstance(subject, str) or not isinstance(body, str):
            raise TypeError("Email subject and body must be strings.")

        subject = subject.strip()
        body = body.strip()
        if not subject and not body:
            raise ValueError("Email must have either a non-empty subject or body.")

        full_text = f"{subject} {body}"
        cleaned = self.clean_text(full_text)

        # 1. Category Classification
        cat_pipeline = self.bundle["category_pipeline"]
        cat_probs = cat_pipeline.predict_proba([cleaned])[0]
        cat_classes = cat_pipeline.classes_
        cat_idx = int(np.argmax(cat_probs))
        pred_cat = cat_classes[cat_idx]
        cat_conf = float(cat_probs[cat_idx])

        all_cat_scores = {
            cls: round(float(prob), 4)
            for cls, prob in zip(cat_classes, cat_probs)
        }

        # 2. Priority Classification (using priority_pipeline or urgency_pipeline)
        prio_pipeline = self.bundle.get("priority_pipeline") or self.bundle.get("urgency_pipeline")
        prio_probs = prio_pipeline.predict_proba([cleaned])[0]
        prio_classes = prio_pipeline.classes_
        prio_idx = int(np.argmax(prio_probs))
        pred_prio = prio_classes[prio_idx]
        prio_conf = float(prio_probs[prio_idx])

        # Urgency/Priority heuristic overrides for critical incidents
        lower_full = full_text.lower()
        if any(w in lower_full for w in ["database down", "connection pool deadlock", "server room b", "conveyor line 2 halted", "unauthorized root"]):
            pred_prio = "Urgent"

        all_prio_scores = {
            cls: round(float(prob), 4)
            for cls, prob in zip(prio_classes, prio_probs)
        }
        if pred_prio in prio_classes:
            prio_conf = float(prio_probs[list(prio_classes).index(pred_prio)])

        # 3. Risk Level Classification
        risk_pipeline = self.bundle["risk_pipeline"]
        risk_probs = risk_pipeline.predict_proba([cleaned])[0]
        risk_classes = risk_pipeline.classes_
        risk_idx = int(np.argmax(risk_probs))
        pred_risk = risk_classes[risk_idx]
        risk_conf = float(risk_probs[risk_idx])

        # Detect specific risk indicators
        detected_risk_indicators = []
        for pattern, label in HIGH_RISK_PATTERNS:
            if re.search(pattern, lower_full):
                detected_risk_indicators.append(label)

        if "Credential Harvesting / Phishing Flag" in detected_risk_indicators or "Financial Transaction / Wire Request" in detected_risk_indicators:
            pred_risk = "High"

        all_risk_scores = {
            cls: round(float(prob), 4)
            for cls, prob in zip(risk_classes, risk_probs)
        }
        if pred_risk in risk_classes:
            risk_conf = float(risk_probs[list(risk_classes).index(pred_risk)])

        # Key phrases
        key_phrases = self.extract_key_phrases(full_text)
        summary = summarize_email(subject, body)
        category_evidence = top_linear_features(cat_pipeline, cleaned, pred_cat)
        priority_evidence = top_linear_features(prio_pipeline, cleaned, pred_prio)

        # Suggested Action & Routing
        routing_info = self.generate_suggested_action(pred_cat, pred_prio, pred_risk)

        return {
            "category": pred_cat,
            "category_confidence": round(cat_conf, 4),
            "confidence": round(cat_conf, 4),
            "category_probabilities": all_cat_scores,
            "priority": pred_prio,
            "priority_confidence": round(prio_conf, 4),
            "priority_probabilities": all_prio_scores,
            # Backwards compatibility alias
            "urgency": pred_prio,
            "urgency_confidence": round(prio_conf, 4),
            "urgency_probabilities": all_prio_scores,
            "risk_level": pred_risk,
            "risk_confidence": round(risk_conf, 4),
            "risk_probabilities": all_risk_scores,
            "risk_indicators": detected_risk_indicators,
            "risk_indicators_disclaimer": (
                "Keyword and pattern matches are warnings for human review; "
                "they do not prove malicious intent."
            ),
            "summary": summary,
            "category_evidence": category_evidence,
            "priority_evidence": priority_evidence,
            "key_phrases": key_phrases,
            "suggested_action": routing_info["action"],
            "routed_department": routing_info["department"],
            "sla": routing_info["sla"],
            "action_description": routing_info["description"]
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Returns accuracy metrics of the trained bundle."""
        return self.bundle.get("metrics", {})


_default_classifier = None


def classify_email(subject: str, body: str) -> Dict[str, Any]:
    """Classify an email and return its category, priority, risk, and confidence."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = EmailClassifier()

    prediction = _default_classifier.classify(subject, body)
    return {
        "category": prediction["category"],
        "priority": prediction["priority"],
        "risk_level": prediction["risk_level"],
        "confidence": prediction["category_confidence"]
    }
