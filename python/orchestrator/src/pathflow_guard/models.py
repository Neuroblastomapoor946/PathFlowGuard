from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Mapping


class QcDecision(StrEnum):
    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


@dataclass(frozen=True)
class SlideIngestionRequest:
    case_id: str
    slide_id: str
    site_id: str
    objective_power: int = 40
    file_bytes: int = 0
    focus_score: float | None = None
    tissue_coverage: float | None = None
    artifact_ratio: float | None = None
    package_path: str | None = None
    notes: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> SlideIngestionRequest:
        return cls(
            case_id=_required_string(data["case_id"]),
            slide_id=_required_string(data["slide_id"]),
            site_id=_required_string(data["site_id"]),
            objective_power=_int_or_default(data.get("objective_power"), 40),
            file_bytes=_int_or_default(data.get("file_bytes"), 0),
            focus_score=_optional_float(data.get("focus_score")),
            tissue_coverage=_optional_float(data.get("tissue_coverage")),
            artifact_ratio=_optional_float(data.get("artifact_ratio")),
            package_path=_optional_string(data.get("package_path")),
            notes=_optional_string(data.get("notes")) or "",
        )

    def with_resolved_metrics(
        self,
        *,
        focus_score: float | None = None,
        tissue_coverage: float | None = None,
        artifact_ratio: float | None = None,
        file_bytes: int | None = None,
        package_path: str | None = None,
    ) -> SlideIngestionRequest:
        return replace(
            self,
            focus_score=self.focus_score if focus_score is None else focus_score,
            tissue_coverage=self.tissue_coverage if tissue_coverage is None else tissue_coverage,
            artifact_ratio=self.artifact_ratio if artifact_ratio is None else artifact_ratio,
            file_bytes=self.file_bytes if file_bytes is None else file_bytes,
            package_path=self.package_path if package_path is None else package_path,
        )

    def needs_extraction(self) -> bool:
        return any(
            value is None
            for value in (self.focus_score, self.tissue_coverage, self.artifact_ratio)
        )


@dataclass(frozen=True)
class QcThresholds:
    review_focus_min: float = 55.0
    reject_focus_min: float = 35.0
    review_tissue_min: float = 0.10
    reject_tissue_min: float = 0.03
    review_artifact_max: float = 0.12
    reject_artifact_max: float = 0.25
    max_file_bytes: int = 5 * 1024 * 1024 * 1024
    supported_objective_powers: tuple[int, ...] = (20, 40)


@dataclass(frozen=True)
class QcDecisionRecord:
    case_id: str
    slide_id: str
    site_id: str
    decision: QcDecision
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StoredJobRecord:
    job_id: str
    created_at: str
    request: SlideIngestionRequest
    decision: QcDecision
    reasons: tuple[str, ...]
    request_record_path: str
    manifest_path: str | None = None
    stored_package_path: str | None = None


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    bytes: int
    blake2b: str


@dataclass(frozen=True)
class PackageManifest:
    generated_at: str
    source_path: str
    entries: tuple[ManifestEntry, ...]
    total_bytes: int


@dataclass(frozen=True)
class ExtractedMetrics:
    focus_score: float
    tissue_coverage: float
    artifact_ratio: float
    tile_count: int
    analyzed_files: tuple[str, ...] = field(default_factory=tuple)


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _required_string(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("required string field is empty")
    return text


def _optional_float(value: object | None) -> float | None:
    text = _optional_string(value)
    if text is None:
        return None
    return float(text)


def _int_or_default(value: object | None, default: int) -> int:
    text = _optional_string(value)
    if text is None:
        return default
    return int(text)
