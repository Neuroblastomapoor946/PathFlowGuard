from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from .models import QcDecision, SlideIngestionRequest, StoredJobRecord


class JobRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    slide_id TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    objective_power INTEGER NOT NULL,
                    file_bytes INTEGER NOT NULL,
                    focus_score REAL NOT NULL,
                    tissue_coverage REAL NOT NULL,
                    artifact_ratio REAL NOT NULL,
                    package_path TEXT,
                    notes TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    request_record_path TEXT NOT NULL,
                    manifest_path TEXT,
                    stored_package_path TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def create_job(self, record: StoredJobRecord) -> None:
        request = record.request
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id,
                    created_at,
                    case_id,
                    slide_id,
                    site_id,
                    objective_power,
                    file_bytes,
                    focus_score,
                    tissue_coverage,
                    artifact_ratio,
                    package_path,
                    notes,
                    decision,
                    reasons_json,
                    request_record_path,
                    manifest_path,
                    stored_package_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.job_id,
                    record.created_at,
                    request.case_id,
                    request.slide_id,
                    request.site_id,
                    request.objective_power,
                    request.file_bytes,
                    request.focus_score,
                    request.tissue_coverage,
                    request.artifact_ratio,
                    request.package_path,
                    request.notes,
                    record.decision.value,
                    json.dumps(record.reasons),
                    record.request_record_path,
                    record.manifest_path,
                    record.stored_package_path,
                ),
            )

    def add_audit_event(
        self,
        *,
        created_at: str,
        job_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (created_at, job_id, event_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (created_at, job_id, event_type, json.dumps(payload, sort_keys=True)),
            )

    def get_job(self, job_id: str) -> StoredJobRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        return _row_to_record(row)

    def list_jobs(self, *, limit: int = 50) -> list[StoredJobRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [_row_to_record(row) for row in rows]

    def summarize(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT decision, COUNT(*) AS count FROM jobs GROUP BY decision"
            ).fetchall()
            total = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        summary = {row["decision"]: int(row["count"]) for row in rows}
        summary["total"] = int(total)
        return summary

    def export_jobs(self, *, limit: int = 100) -> list[dict[str, object]]:
        return [asdict(record) for record in self.list_jobs(limit=limit)]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def _row_to_record(row: sqlite3.Row) -> StoredJobRecord:
    request = SlideIngestionRequest(
        case_id=row["case_id"],
        slide_id=row["slide_id"],
        site_id=row["site_id"],
        objective_power=row["objective_power"],
        file_bytes=row["file_bytes"],
        focus_score=row["focus_score"],
        tissue_coverage=row["tissue_coverage"],
        artifact_ratio=row["artifact_ratio"],
        package_path=row["package_path"],
        notes=row["notes"],
    )
    return StoredJobRecord(
        job_id=row["job_id"],
        created_at=row["created_at"],
        request=request,
        decision=QcDecision(row["decision"]),
        reasons=tuple(json.loads(row["reasons_json"])),
        request_record_path=row["request_record_path"],
        manifest_path=row["manifest_path"],
        stored_package_path=row["stored_package_path"],
    )
