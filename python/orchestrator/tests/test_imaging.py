from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from pathlib import Path

from PIL import Image

from pathflow_guard.imaging import extract_metrics_from_package, runtime_capabilities


class ImagingTests(unittest.TestCase):
    def test_extract_metrics_from_focused_tile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "focused.png"
            image = Image.new("RGB", (8, 8), color=(240, 240, 240))
            for x in range(1, 7):
                image.putpixel((x, 3), (80, 80, 80))
                image.putpixel((x, 4), (80, 80, 80))
            image.save(image_path)

            metrics = extract_metrics_from_package(root)
            self.assertGreater(metrics.focus_score, 40.0)
            self.assertGreater(metrics.tissue_coverage, 0.10)
            self.assertLess(metrics.artifact_ratio, 0.10)

    def test_extract_metrics_from_artifact_heavy_tile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "artifact.png"
            image = Image.new("RGB", (8, 8), color=(250, 250, 250))
            image.putpixel((1, 1), (255, 0, 0))
            image.putpixel((3, 2), (0, 0, 255))
            image.putpixel((4, 5), (0, 0, 0))
            image.save(image_path)

            metrics = extract_metrics_from_package(root)
            self.assertGreater(metrics.artifact_ratio, 0.05)

    def test_extract_metrics_from_fake_svs_uses_openslide_sampling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            slide_path = Path(temp_dir) / "sample.svs"
            slide_path.write_bytes(b"fake-svs")

            with mock.patch("pathflow_guard.imaging._import_openslide", return_value=FakeOpenSlideModule()):
                metrics = extract_metrics_from_package(slide_path, max_tiles=4)

            self.assertEqual(metrics.tile_count, 4)
            self.assertGreater(metrics.focus_score, 10.0)
            self.assertGreater(metrics.tissue_coverage, 0.05)
            self.assertTrue(all(".svs#tile-" in entry for entry in metrics.analyzed_files))

    def test_runtime_capabilities_reports_supported_formats(self) -> None:
        capabilities = runtime_capabilities()
        self.assertIn(".svs", capabilities["supported_wsi_extensions"])
        self.assertIn(".png", capabilities["supported_raster_extensions"])


class FakeOpenSlideModule:
    PROPERTY_NAME_BOUNDS_X = "openslide.bounds-x"
    PROPERTY_NAME_BOUNDS_Y = "openslide.bounds-y"
    PROPERTY_NAME_BOUNDS_WIDTH = "openslide.bounds-width"
    PROPERTY_NAME_BOUNDS_HEIGHT = "openslide.bounds-height"

    class OpenSlide:
        def __init__(self, filename: str) -> None:
            self.filename = filename
            self.level_dimensions = ((1024, 768),)
            self.properties = {
                "openslide.bounds-x": "64",
                "openslide.bounds-y": "32",
                "openslide.bounds-width": "896",
                "openslide.bounds-height": "640",
            }

        @staticmethod
        def detect_format(filename: str) -> str | None:
            return "aperio" if filename.endswith(".svs") else None

        def read_region(
            self,
            location: tuple[int, int],
            level: int,
            size: tuple[int, int],
        ) -> Image.Image:
            image = Image.new("RGBA", size, color=(245, 245, 245, 255))
            offset = ((location[0] // 64) + (location[1] // 64)) % 2
            for y in range(32, max(33, size[1] - 32)):
                for x in range(32, max(33, size[0] - 32)):
                    if ((x // 16) + (y // 16) + offset) % 2 == 0:
                        image.putpixel((x, y), (120, 80, 140, 255))
            return image

        def close(self) -> None:
            return None


if __name__ == "__main__":
    unittest.main()
