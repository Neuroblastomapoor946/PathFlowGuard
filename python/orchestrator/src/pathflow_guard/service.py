from __future__ import annotations

from .models import QcDecision, QcDecisionRecord, QcThresholds, SlideIngestionRequest


def evaluate_request(
    request: SlideIngestionRequest,
    thresholds: QcThresholds | None = None,
) -> QcDecisionRecord:
    limits = thresholds or QcThresholds()
    reasons: list[str] = []
    focus_score = _require_metric(request.focus_score, "focus_score")
    tissue_coverage = _require_metric(request.tissue_coverage, "tissue_coverage")
    artifact_ratio = _require_metric(request.artifact_ratio, "artifact_ratio")

    if request.objective_power not in limits.supported_objective_powers:
        reasons.append("unsupported_objective_power")

    if request.file_bytes <= 0:
        reasons.append("invalid_file_size")
    elif request.file_bytes > limits.max_file_bytes:
        reasons.append("file_too_large")

    if focus_score < limits.reject_focus_min:
        reasons.append("focus_below_reject_threshold")
    elif focus_score < limits.review_focus_min:
        reasons.append("focus_below_review_threshold")

    if tissue_coverage < limits.reject_tissue_min:
        reasons.append("tissue_below_reject_threshold")
    elif tissue_coverage < limits.review_tissue_min:
        reasons.append("tissue_below_review_threshold")

    if artifact_ratio > limits.reject_artifact_max:
        reasons.append("artifact_above_reject_threshold")
    elif artifact_ratio > limits.review_artifact_max:
        reasons.append("artifact_above_review_threshold")

    decision = _select_decision(reasons)
    return QcDecisionRecord(
        case_id=request.case_id,
        slide_id=request.slide_id,
        site_id=request.site_id,
        decision=decision,
        reasons=tuple(reasons),
    )


def _select_decision(reasons: list[str]) -> QcDecision:
    if any(reason.endswith("_reject_threshold") for reason in reasons):
        return QcDecision.REJECT

    if "unsupported_objective_power" in reasons or "file_too_large" in reasons:
        return QcDecision.REVIEW

    if any(reason.endswith("_review_threshold") for reason in reasons):
        return QcDecision.REVIEW

    if "invalid_file_size" in reasons:
        return QcDecision.REJECT

    return QcDecision.ACCEPT


def _require_metric(value: float | None, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is required unless it can be extracted from image tiles")
    return value
