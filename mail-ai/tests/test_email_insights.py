"""Tests for extractive email summaries and linear-model evidence."""

import unittest

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from models.email_insights import summarize_email, top_linear_features


class TestEmailInsights(unittest.TestCase):
    def test_short_email_summary_preserves_source_text(self):
        summary = summarize_email("Invoice issue", "Please correct the duplicate charge.")
        self.assertEqual(summary, "Invoice issue Please correct the duplicate charge.")

    def test_summary_uses_leading_sentences(self):
        body = "The server is unavailable. Checkout requests are failing. The team is investigating."
        summary = summarize_email("Production incident", body)
        self.assertEqual(summary, "Production incident The server is unavailable.")
        self.assertNotIn("The team is investigating", summary)

    def test_punctuation_free_email_is_bounded_and_extractive(self):
        body = " ".join(["urgent", "database", "support"] * 30)
        summary = summarize_email("", body, max_chars=100)
        self.assertLessEqual(len(summary), 100)
        self.assertTrue(body.startswith(summary.removesuffix("...")))

    def test_email_without_text_returns_empty_summary(self):
        self.assertEqual(summarize_email("  ", "\n\t"), "")

    def test_linear_evidence_returns_present_positive_features(self):
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LogisticRegression(random_state=7, max_iter=1000))
        ])
        pipeline.fit(
            [
                "enterprise software sales demo pricing",
                "sales team wants a product demo",
                "password reset security incident",
                "security team investigates compromised account"
            ],
            ["Sales", "Sales", "Security", "Security"]
        )

        features = top_linear_features(pipeline, "enterprise sales demo", "Sales")
        vocabulary = set(pipeline.named_steps["tfidf"].get_feature_names_out())
        self.assertTrue(features)
        self.assertTrue(set(features).issubset(vocabulary))

    def test_unsupported_model_returns_no_evidence(self):
        self.assertEqual(top_linear_features(object(), "email text", "Sales"), [])


if __name__ == "__main__":
    unittest.main()