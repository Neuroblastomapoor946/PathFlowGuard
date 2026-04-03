from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pathflow_guard.manifest import build_manifest, write_manifest


class ManifestTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "nested").mkdir()
            (root / "nested" / "b.txt").write_text("beta", encoding="utf-8")
            (root / "a.txt").write_text("alpha", encoding="utf-8")

            first = build_manifest(root)
            second = build_manifest(root)

            self.assertEqual(first, second)
            self.assertEqual([entry.path for entry in first.entries], ["a.txt", "nested/b.txt"])

    def test_write_manifest_persists_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "package"
            source.mkdir()
            (source / "slide.txt").write_text("payload", encoding="utf-8")

            manifest = build_manifest(source)
            destination = root / "manifest.json"
            write_manifest(manifest, destination)

            loaded = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(loaded["entries"][0]["path"], "slide.txt")


if __name__ == "__main__":
    unittest.main()

