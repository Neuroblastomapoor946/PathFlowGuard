from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pathflow_guard.config import build_workspace
from pathflow_guard.database import JobRepository
from pathflow_guard.pipeline import IngestionPipeline
from pathflow_guard.web import PathFlowGuardServer


class WebTests(unittest.TestCase):
    def test_server_healthz_and_ingest_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = build_workspace(Path(temp_dir) / "runtime")
            repository = JobRepository(workspace.db_path)
            pipeline = IngestionPipeline(workspace, repository)
            pipeline.initialize()

            server = PathFlowGuardServer(("127.0.0.1", 0), workspace, repository, pipeline)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"

            try:
                with urlopen(f"{base_url}/healthz") as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")

                form_data = urlencode(
                    {
                        "case_id": "CASE-WEB-1",
                        "slide_id": "SLIDE-WEB-1",
                        "site_id": "SITE-WEB-1",
                        "objective_power": 40,
                        "file_bytes": 1000,
                        "focus_score": 75.0,
                        "tissue_coverage": 0.35,
                        "artifact_ratio": 0.02,
                    }
                ).encode("utf-8")
                request = Request(f"{base_url}/ingest", data=form_data, method="POST")
                with urlopen(request) as response:
                    landing_url = response.geturl()
                self.assertIn("/jobs/job-", landing_url)

                with urlopen(f"{base_url}/api/jobs") as response:
                    jobs = json.loads(response.read().decode("utf-8"))
                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0]["decision"], "accept")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
