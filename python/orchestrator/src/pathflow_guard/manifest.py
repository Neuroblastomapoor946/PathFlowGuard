from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import ManifestEntry, PackageManifest


def build_manifest(source_path: Path) -> PackageManifest:
    resolved_source = source_path.resolve()
    if not resolved_source.exists():
        raise FileNotFoundError(f"Package path does not exist: {resolved_source}")

    entries = tuple(_collect_entries(resolved_source))
    total_bytes = sum(entry.bytes for entry in entries)
    return PackageManifest(
        generated_at=_timestamp(),
        source_path=str(resolved_source),
        entries=entries,
        total_bytes=total_bytes,
    )


def write_manifest(manifest: PackageManifest, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")


def _collect_entries(source_path: Path) -> list[ManifestEntry]:
    if source_path.is_file():
        return [_manifest_entry_for(source_path, source_path.parent)]

    entries = [
        _manifest_entry_for(path, source_path)
        for path in sorted(source_path.rglob("*"))
        if path.is_file()
    ]
    return entries


def _manifest_entry_for(path: Path, root: Path) -> ManifestEntry:
    relative_path = path.relative_to(root).as_posix()
    return ManifestEntry(
        path=relative_path,
        bytes=path.stat().st_size,
        blake2b=_hash_file(path),
    )


def _hash_file(path: Path) -> str:
    digest = hashlib.blake2b(digest_size=32)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

