from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .config import WorkspacePaths, ensure_workspace
from .database import JobRepository
from .imaging import extract_metrics_from_package, measure_path_bytes
from .manifest import build_manifest, write_manifest
from .models import ExtractedMetrics, QcDecision, SlideIngestionRequest, StoredJobRecord
from .service import evaluate_request


class IngestionPipeline:
    def __init__(self, workspace: WorkspacePaths, repository: JobRepository) -> None:
        self._workspace = workspace
        self._repository = repository

    def initialize(self) -> None:
        ensure_workspace(self._workspace)
        self._repository.initialize()

    def ingest_request(
        self,
        request: SlideIngestionRequest,
        *,
        request_source_path: Path | None = None,
    ) -> StoredJobRecord:
        self.initialize()

        created_at = _timestamp()
        job_id = _build_job_id()
        request, package_path, extracted_metrics = resolve_request_context(
            request,
            request_source_path=request_source_path,
        )
        evaluation = evaluate_request(request)

        request_record_path = self._workspace.requests_dir / f"{job_id}.json"
        request_record_path.write_text(
            json.dumps(asdict(request), indent=2),
            encoding="utf-8",
        )

        manifest_path: Path | None = None
        stored_package_path: Path | None = None
        if package_path is not None:
            manifest = build_manifest(package_path)
            manifest_path = self._workspace.manifests_dir / f"{job_id}.json"
            write_manifest(manifest, manifest_path)
            stored_package_path = self._copy_package(package_path, evaluation.decision, job_id)

        record = StoredJobRecord(
            job_id=job_id,
            created_at=created_at,
            request=request,
            decision=evaluation.decision,
            reasons=evaluation.reasons,
            request_record_path=str(request_record_path),
            manifest_path=str(manifest_path) if manifest_path is not None else None,
            stored_package_path=str(stored_package_path) if stored_package_path is not None else None,
        )
        self._repository.create_job(record)
        audit_events: list[dict[str, object]] = []
        if extracted_metrics is not None:
            metrics_event = {
                "created_at": created_at,
                "event_type": "metrics_extracted",
                "payload": asdict(extracted_metrics),
            }
            self._repository.add_audit_event(
                created_at=created_at,
                job_id=job_id,
                event_type=metrics_event["event_type"],
                payload=metrics_event["payload"],
            )
            audit_events.append(metrics_event)

        ingest_event = {
            "created_at": created_at,
            "event_type": "job_ingested",
            "payload": {
                "decision": record.decision.value,
                "reasons": list(record.reasons),
                "manifest_path": record.manifest_path,
                "stored_package_path": record.stored_package_path,
            },
        }
        self._repository.add_audit_event(
            created_at=created_at,
            job_id=job_id,
            event_type=ingest_event["event_type"],
            payload=ingest_event["payload"],
        )
        audit_events.append(ingest_event)
        self._write_audit_record(job_id, audit_events)
        return record

    def _copy_package(self, source_path: Path, decision: QcDecision, job_id: str) -> Path:
        destination_root = _decision_directory(self._workspace, decision)
        destination_root.mkdir(parents=True, exist_ok=True)
        destination_path = destination_root / job_id

        if source_path.is_dir():
            shutil.copytree(source_path, destination_path)
            return destination_path

        destination_path.mkdir(parents=True, exist_ok=True)
        target = destination_path / source_path.name
        shutil.copy2(source_path, target)
        return target

    def _write_audit_record(self, job_id: str, events: list[dict[str, object]]) -> Path:
        audit_path = self._workspace.audit_dir / f"{job_id}.json"
        audit_path.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "events": events,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return audit_path


def _build_job_id() -> str:
    return f"job-{datetime.now(UTC):%Y%m%d%H%M%S}-{uuid4().hex[:8]}"


def resolve_request_context(
    request: SlideIngestionRequest,
    *,
    request_source_path: Path | None = None,
) -> tuple[SlideIngestionRequest, Path | None, ExtractedMetrics | None]:
    package_path = _resolve_package_path(request.package_path, request_source_path)
    if package_path is None:
        return request, None, None

    resolved_request = request.with_resolved_metrics(package_path=str(package_path))
    if resolved_request.file_bytes <= 0:
        resolved_request = resolved_request.with_resolved_metrics(
            file_bytes=measure_path_bytes(package_path),
        )

    if not resolved_request.needs_extraction():
        return resolved_request, package_path, None

    extracted_metrics = extract_metrics_from_package(package_path)
    resolved_request = resolved_request.with_resolved_metrics(
        focus_score=extracted_metrics.focus_score,
        tissue_coverage=extracted_metrics.tissue_coverage,
        artifact_ratio=extracted_metrics.artifact_ratio,
    )
    return resolved_request, package_path, extracted_metrics


def _resolve_package_path(
    package_path: str | None,
    request_source_path: Path | None,
) -> Path | None:
    if not package_path:
        return None

    candidate = Path(package_path)
    if not candidate.is_absolute() and request_source_path is not None:
        candidate = request_source_path.parent / candidate
    return candidate.resolve()


def _decision_directory(workspace: WorkspacePaths, decision: QcDecision) -> Path:
    if decision is QcDecision.ACCEPT:
        return workspace.accepted_dir
    if decision is QcDecision.REVIEW:
        return workspace.review_dir
    return workspace.rejected_dir


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
