from __future__ import annotations

import unittest

from pathflow_guard import QcDecision, SlideIngestionRequest, evaluate_request


def make_request(**overrides: object) -> SlideIngestionRequest:
    data: dict[str, object] = {
        "case_id": "CASE-1",
        "slide_id": "SLIDE-1",
        "site_id": "SITE-1",
        "objective_power": 40,
        "file_bytes": 512_000_000,
        "focus_score": 80.0,
        "tissue_coverage": 0.35,
        "artifact_ratio": 0.02,
    }
    data.update(overrides)
    return SlideIngestionRequest(**data)


class EvaluateRequestTests(unittest.TestCase):
    def test_accepts_clean_slide(self) -> None:
        result = evaluate_request(make_request())
        self.assertEqual(result.decision, QcDecision.ACCEPT)
        self.assertEqual(result.reasons, ())

    def test_routes_borderline_slide_to_review(self) -> None:
        result = evaluate_request(make_request(focus_score=45.0))
        self.assertEqual(result.decision, QcDecision.REVIEW)
        self.assertIn("focus_below_review_threshold", result.reasons)

    def test_rejects_severely_bad_slide(self) -> None:
        result = evaluate_request(make_request(artifact_ratio=0.4))
        self.assertEqual(result.decision, QcDecision.REJECT)
        self.assertIn("artifact_above_reject_threshold", result.reasons)

    def test_rejects_invalid_empty_file(self) -> None:
        result = evaluate_request(make_request(file_bytes=0))
        self.assertEqual(result.decision, QcDecision.REJECT)
        self.assertIn("invalid_file_size", result.reasons)

    def test_reviews_unsupported_objective_power(self) -> None:
        result = evaluate_request(make_request(objective_power=63))
        self.assertEqual(result.decision, QcDecision.REVIEW)
        self.assertIn("unsupported_objective_power", result.reasons)


if __name__ == "__main__":
    unittest.main()

