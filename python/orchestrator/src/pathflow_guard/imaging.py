from __future__ import annotations

import ctypes
import math
import os
import platform
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFile

from .models import ExtractedMetrics

ImageFile.LOAD_TRUNCATED_IMAGES = False

SUPPORTED_IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".pgm",
    ".png",
    ".ppm",
    ".tif",
    ".tiff",
}
SUPPORTED_WSI_EXTENSIONS = {
    ".bif",
    ".mrxs",
    ".ndpi",
    ".scn",
    ".svs",
    ".svslide",
    ".vms",
    ".vmu",
}
AMBIGUOUS_WSI_EXTENSIONS = {
    ".tif",
    ".tiff",
}
SLIDE_TILE_SIZE = 256

_DLL_DIR_HANDLES: list[object] = []
_OPENSLIDE_RUNTIME_READY = False


def _import_openslide() -> object | None:
    _ensure_openslide_runtime()
    try:
        import openslide as openslide_module
    except (ImportError, OSError):
        return None
    return openslide_module


def runtime_capabilities() -> dict[str, object]:
    openslide_module = _import_openslide()
    payload: dict[str, object] = {
        "openslide_available": openslide_module is not None,
        "supported_raster_extensions": sorted(SUPPORTED_IMAGE_EXTENSIONS),
        "supported_wsi_extensions": sorted(SUPPORTED_WSI_EXTENSIONS | AMBIGUOUS_WSI_EXTENSIONS),
    }
    if openslide_module is None:
        return payload

    payload["openslide_module_path"] = getattr(openslide_module, "__file__", None)
    payload["openslide_version"] = getattr(openslide_module, "__version__", None)
    return payload


def extract_metrics_from_package(package_path: Path, *, max_tiles: int = 24) -> ExtractedMetrics:
    resolved = package_path.resolve()
    slide_path = find_slide_path(resolved)
    if slide_path is not None:
        return _extract_metrics_from_slide(slide_path, max_tiles=max_tiles)

    image_paths = collect_image_paths(resolved)[:max_tiles]
    if not image_paths:
        raise ValueError(f"No supported image tiles found under {package_path}")

    return _aggregate_metric_images(_iter_raster_images(image_paths), len(image_paths))


def find_slide_path(package_path: Path) -> Path | None:
    resolved = package_path.resolve()
    if resolved.is_file():
        return _direct_slide_path(resolved)

    if not resolved.exists():
        raise FileNotFoundError(f"Package path does not exist: {resolved}")

    candidates = sorted(
        path
        for path in resolved.rglob("*")
        if path.is_file() and _has_slide_like_extension(path)
    )
    if not candidates:
        return None

    openslide_module = _import_openslide()
    for candidate in candidates:
        direct = _direct_slide_path(candidate, openslide_module=openslide_module)
        if direct is not None:
            return direct
    return None


def collect_image_paths(package_path: Path) -> list[Path]:
    resolved = package_path.resolve()
    if resolved.is_file():
        return [resolved] if _is_supported_raster_image(resolved) else []

    if not resolved.exists():
        raise FileNotFoundError(f"Package path does not exist: {resolved}")

    return sorted(
        path
        for path in resolved.rglob("*")
        if path.is_file() and _is_supported_raster_image(path)
    )


def measure_path_bytes(package_path: Path) -> int:
    resolved = package_path.resolve()
    if resolved.is_file():
        return resolved.stat().st_size

    if not resolved.exists():
        raise FileNotFoundError(f"Package path does not exist: {resolved}")

    return sum(path.stat().st_size for path in resolved.rglob("*") if path.is_file())


def _extract_metrics_from_slide(slide_path: Path, *, max_tiles: int) -> ExtractedMetrics:
    openslide_module = _import_openslide()
    if openslide_module is None:
        raise RuntimeError(
            "OpenSlide support is unavailable. Install openslide-python and openslide-bin."
        )

    vendor = _detect_slide_vendor(openslide_module, slide_path)
    if vendor is None:
        raise ValueError(f"OpenSlide could not recognize slide format: {slide_path}")

    slide = openslide_module.OpenSlide(str(slide_path))
    try:
        tile_requests = list(_build_slide_tile_requests(openslide_module, slide, max_tiles))
        if not tile_requests:
            raise ValueError(f"No valid tile samples could be generated for slide {slide_path}")

        labeled_images = []
        for index, (location, size) in enumerate(tile_requests, start=1):
            region = slide.read_region(location, 0, size)
            label = f"{slide_path}#tile-{index}@{location[0]},{location[1]}:{size[0]}x{size[1]}"
            labeled_images.append((label, _prepare_slide_region(region)))
        return _aggregate_metric_images(labeled_images, len(labeled_images))
    finally:
        slide.close()


def _aggregate_metric_images(
    labeled_images: Iterable[tuple[str, Image.Image]],
    tile_count: int,
) -> ExtractedMetrics:
    weighted_focus = 0.0
    weighted_tissue = 0.0
    weighted_artifact = 0.0
    total_pixels = 0
    analyzed_files: list[str] = []

    for label, image in labeled_images:
        focus_score, tissue_coverage, artifact_ratio, pixel_count = _measure_image(image)
        weighted_focus += focus_score * pixel_count
        weighted_tissue += tissue_coverage * pixel_count
        weighted_artifact += artifact_ratio * pixel_count
        total_pixels += pixel_count
        analyzed_files.append(label)

    if total_pixels == 0:
        raise ValueError("No pixels were analyzed while extracting metrics")

    return ExtractedMetrics(
        focus_score=round(weighted_focus / total_pixels, 2),
        tissue_coverage=round(weighted_tissue / total_pixels, 4),
        artifact_ratio=round(weighted_artifact / total_pixels, 4),
        tile_count=tile_count,
        analyzed_files=tuple(analyzed_files),
    )


def _iter_raster_images(image_paths: list[Path]) -> Iterable[tuple[str, Image.Image]]:
    for path in image_paths:
        with Image.open(path) as image:
            yield str(path), _prepare_image(image)


def _prepare_image(image: Image.Image) -> Image.Image:
    prepared = image.convert("RGB")
    if max(prepared.size) > 256:
        prepared.thumbnail((256, 256))
    return prepared


def _prepare_slide_region(region: Image.Image) -> Image.Image:
    rgba_region = region.convert("RGBA")
    background = Image.new("RGBA", rgba_region.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(background, rgba_region).convert("RGB")
    return _prepare_image(composited)


def _build_slide_tile_requests(
    openslide_module: object,
    slide: object,
    max_tiles: int,
) -> Iterable[tuple[tuple[int, int], tuple[int, int]]]:
    slide_width, slide_height = slide.level_dimensions[0]
    bounds_x, bounds_y, bounds_width, bounds_height = _slide_bounds(openslide_module, slide)

    if bounds_width <= 0 or bounds_height <= 0:
        bounds_x = 0
        bounds_y = 0
        bounds_width = slide_width
        bounds_height = slide_height

    columns, rows = _grid_shape(bounds_width, bounds_height, max_tiles)
    for row in range(rows):
        for column in range(columns):
            if (row * columns) + column >= max_tiles:
                return

            center_x = bounds_x + int(((column + 0.5) * bounds_width) / columns)
            center_y = bounds_y + int(((row + 0.5) * bounds_height) / rows)
            left = max(0, min(center_x - (SLIDE_TILE_SIZE // 2), slide_width - 1))
            top = max(0, min(center_y - (SLIDE_TILE_SIZE // 2), slide_height - 1))
            width = min(SLIDE_TILE_SIZE, slide_width - left)
            height = min(SLIDE_TILE_SIZE, slide_height - top)
            if width < 16 or height < 16:
                continue
            yield (left, top), (width, height)


def _slide_bounds(openslide_module: object, slide: object) -> tuple[int, int, int, int]:
    properties = slide.properties
    width, height = slide.level_dimensions[0]
    return (
        _property_int(properties, openslide_module.PROPERTY_NAME_BOUNDS_X, 0),
        _property_int(properties, openslide_module.PROPERTY_NAME_BOUNDS_Y, 0),
        _property_int(properties, openslide_module.PROPERTY_NAME_BOUNDS_WIDTH, width),
        _property_int(properties, openslide_module.PROPERTY_NAME_BOUNDS_HEIGHT, height),
    )


def _property_int(properties: object, key: str, default: int) -> int:
    value = properties.get(key)
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _grid_shape(width: int, height: int, max_tiles: int) -> tuple[int, int]:
    aspect_ratio = width / max(height, 1)
    columns = max(1, min(max_tiles, math.ceil(math.sqrt(max_tiles * aspect_ratio))))
    rows = max(1, math.ceil(max_tiles / columns))
    return columns, rows


def _measure_image(image: Image.Image) -> tuple[float, float, float, int]:
    width, height = image.size
    pixel_access = image.load()
    pixels = [pixel_access[x, y] for y in range(height) for x in range(width)]
    grayscale = [_grayscale(pixel) for pixel in pixels]
    pixel_count = width * height

    focus_score = _focus_score(grayscale, width, height)
    tissue_coverage = _tissue_coverage(grayscale)
    artifact_ratio = _artifact_ratio(pixels, grayscale, width, height)
    return focus_score, tissue_coverage, artifact_ratio, pixel_count


def _grayscale(pixel: tuple[int, int, int]) -> float:
    red, green, blue = pixel
    return (0.299 * red) + (0.587 * green) + (0.114 * blue)


def _focus_score(grayscale: list[float], width: int, height: int) -> float:
    if width < 3 or height < 3:
        return 0.0

    total_response = 0.0
    sample_count = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            index = (y * width) + x
            center = grayscale[index]
            north = grayscale[index - width]
            south = grayscale[index + width]
            east = grayscale[index + 1]
            west = grayscale[index - 1]
            laplacian = abs((4.0 * center) - north - south - east - west)
            total_response += laplacian
            sample_count += 1

    if sample_count == 0:
        return 0.0

    return total_response / sample_count


def _tissue_coverage(grayscale: list[float]) -> float:
    if not grayscale:
        return 0.0

    tissue_pixels = sum(1 for value in grayscale if value < 225.0)
    return tissue_pixels / len(grayscale)


def _artifact_ratio(
    pixels: list[tuple[int, int, int]],
    grayscale: list[float],
    width: int,
    height: int,
) -> float:
    if width < 3 or height < 3:
        return 0.0

    artifact_pixels = 0
    sample_count = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            index = (y * width) + x
            local_mean = (
                grayscale[index - width - 1]
                + grayscale[index - width]
                + grayscale[index - width + 1]
                + grayscale[index - 1]
                + grayscale[index + 1]
                + grayscale[index + width - 1]
                + grayscale[index + width]
                + grayscale[index + width + 1]
            ) / 8.0
            gray = grayscale[index]
            red, green, blue = pixels[index]
            chroma = max(red, green, blue) - min(red, green, blue)
            isolated_spike = abs(gray - local_mean) > 75.0 and (gray < 25.0 or gray > 240.0)
            saturated_marker = chroma > 110 and max(red, green, blue) > 180
            if isolated_spike or saturated_marker:
                artifact_pixels += 1
            sample_count += 1

    if sample_count == 0:
        return 0.0

    return artifact_pixels / sample_count


def _direct_slide_path(package_path: Path, openslide_module: object | None = None) -> Path | None:
    if _is_known_slide_extension(package_path):
        return package_path

    if not _is_ambiguous_slide_extension(package_path):
        return None

    module = openslide_module or _import_openslide()
    if module is not None and _detect_slide_vendor(module, package_path) is not None:
        return package_path
    return None


def _has_slide_like_extension(path: Path) -> bool:
    return _is_known_slide_extension(path) or _is_ambiguous_slide_extension(path)


def _is_known_slide_extension(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_WSI_EXTENSIONS


def _is_ambiguous_slide_extension(path: Path) -> bool:
    return path.suffix.lower() in AMBIGUOUS_WSI_EXTENSIONS


def _is_supported_raster_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and not _is_known_slide_extension(path)


def _detect_slide_vendor(openslide_module: object, slide_path: Path) -> str | None:
    try:
        return openslide_module.OpenSlide.detect_format(str(slide_path))
    except Exception:
        return None


def _ensure_openslide_runtime() -> None:
    global _OPENSLIDE_RUNTIME_READY
    if _OPENSLIDE_RUNTIME_READY or platform.system() != "Windows":
        return

    candidate_directories: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate_directories.append(Path(sys._MEIPASS))

    try:
        import openslide_bin  # type: ignore
    except ImportError:
        openslide_bin = None
    if openslide_bin is not None:
        candidate_directories.append(Path(openslide_bin.__file__).resolve().parent)

    conda_bin = Path(os.environ.get("CONDA_PREFIX", sys.base_prefix)) / "Library" / "bin"
    candidate_directories.append(conda_bin)

    seen: set[Path] = set()
    for directory in candidate_directories:
        if directory in seen or not directory.exists():
            continue
        seen.add(directory)
        if hasattr(os, "add_dll_directory"):
            _DLL_DIR_HANDLES.append(os.add_dll_directory(str(directory)))
        dll_path = directory / "libopenslide-1.dll"
        if dll_path.exists():
            try:
                ctypes.CDLL(str(dll_path))
            except OSError:
                continue
            _OPENSLIDE_RUNTIME_READY = True
            return

    _OPENSLIDE_RUNTIME_READY = True
