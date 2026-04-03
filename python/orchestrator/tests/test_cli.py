from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from PIL import Image

from pathflow_guard.cli import main


class CliTests(unittest.TestCase):
    def test_doctor_reports_runtime_details(self) -> None:
        with io.StringIO() as buffer, redirect_stdout(buffer):
            exit_code = main(["doctor"])
            output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        payload = json.loads(output)
        self.assertIn("runtime", payload)
        self.assertIn("samples_available", payload)

    def test_cli_smoke_flow_from_request_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "runtime"
            package_dir = root / "packages" / "case-1"
            package_dir.mkdir(parents=True)

            image = Image.new("RGB", (8, 8), color=(240, 240, 240))
            for x in range(1, 7):
                image.putpixel((x, 3), (90, 90, 90))
                image.putpixel((x, 4), (90, 90, 90))
            image.save(package_dir / "tile.png")

            request_path = root / "requests" / "accept.json"
            request_path.parent.mkdir(parents=True)
            request_path.write_text(
                json.dumps(
                    {
                        "case_id": "CASE-CLI-1",
                        "slide_id": "SLIDE-CLI-1",
                        "site_id": "SITE-CLI-1",
                        "objective_power": 40,
                        "file_bytes": 0,
                        "package_path": "../packages/case-1",
                        "notes": "cli smoke",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(main(["init", "--workspace", str(workspace)]), 0)

            with io.StringIO() as buffer, redirect_stdout(buffer):
                evaluate_exit = main(["evaluate", str(request_path)])
                evaluation = json.loads(buffer.getvalue())
            self.assertEqual(evaluate_exit, 0)
            self.assertEqual(evaluation["evaluation"]["decision"], "accept")

            with io.StringIO() as buffer, redirect_stdout(buffer):
                ingest_exit = main(["ingest", str(request_path), "--workspace", str(workspace)])
                ingested = json.loads(buffer.getvalue())
            self.assertEqual(ingest_exit, 0)
            self.assertEqual(ingested["decision"], "accept")

            with io.StringIO() as buffer, redirect_stdout(buffer):
                report_exit = main(["report", "--workspace", str(workspace)])
                report = json.loads(buffer.getvalue())
            self.assertEqual(report_exit, 0)
            self.assertEqual(report["summary"]["total"], 1)

            with io.StringIO() as buffer, redirect_stdout(buffer):
                extract_exit = main(["extract", str(package_dir)])
                extracted = json.loads(buffer.getvalue())
            self.assertEqual(extract_exit, 0)
            self.assertGreater(extracted["focus_score"], 0)


if __name__ == "__main__":
    unittest.main()
