from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from pathflow_guard.config import build_workspace
from pathflow_guard.database import JobRepository
from pathflow_guard.models import QcDecision, SlideIngestionRequest
from pathflow_guard.pipeline import IngestionPipeline


class PipelineTests(unittest.TestCase):
    def test_ingest_request_persists_job_and_routes_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_dir = temp_root / "incoming" / "case-1"
            package_dir.mkdir(parents=True)
            image = Image.new("RGB", (8, 8), color=(240, 240, 240))
            for x in range(1, 7):
                image.putpixel((x, 3), (90, 90, 90))
                image.putpixel((x, 4), (90, 90, 90))
            image.save(package_dir / "tile.png")

            workspace = build_workspace(temp_root / "runtime")
            repository = JobRepository(workspace.db_path)
            pipeline = IngestionPipeline(workspace, repository)
            request = SlideIngestionRequest(
                case_id="CASE-1",
                slide_id="SLIDE-1",
                site_id="SITE-1",
                objective_power=40,
                file_bytes=0,
                package_path=str(package_dir),
                notes="test ingest",
            )

            record = pipeline.ingest_request(request)

            self.assertEqual(record.decision, QcDecision.ACCEPT)
            self.assertIsNotNone(record.request.focus_score)
            self.assertIsNotNone(record.request.tissue_coverage)
            self.assertIsNotNone(record.request.artifact_ratio)
            self.assertTrue(Path(record.request_record_path).exists())
            self.assertTrue(Path(record.manifest_path or "").exists())
            self.assertTrue(Path(record.stored_package_path or "").exists())
            self.assertTrue((workspace.audit_dir / f"{record.job_id}.json").exists())

            stored = repository.get_job(record.job_id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.job_id, record.job_id)
            self.assertEqual(stored.decision, QcDecision.ACCEPT)

    def test_ingest_request_routes_review_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = build_workspace(Path(temp_dir) / "runtime")
            repository = JobRepository(workspace.db_path)
            pipeline = IngestionPipeline(workspace, repository)
            request = SlideIngestionRequest(
                case_id="CASE-2",
                slide_id="SLIDE-2",
                site_id="SITE-1",
                objective_power=40,
                file_bytes=1000,
                focus_score=50.0,
                tissue_coverage=0.44,
                artifact_ratio=0.02,
            )

            record = pipeline.ingest_request(request)
            self.assertEqual(record.decision, QcDecision.REVIEW)
            self.assertIsNone(record.manifest_path)
            self.assertIsNone(record.stored_package_path)
            self.assertTrue((workspace.audit_dir / f"{record.job_id}.json").exists())


if __name__ == "__main__":
    unittest.main()
