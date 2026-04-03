from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    db_path: Path
    requests_dir: Path
    manifests_dir: Path
    accepted_dir: Path
    review_dir: Path
    rejected_dir: Path
    audit_dir: Path


def build_workspace(root: Path | str | None = None) -> WorkspacePaths:
    workspace_root = Path(root).resolve() if root is not None else (Path.cwd() / "runtime").resolve()
    return WorkspacePaths(
        root=workspace_root,
        db_path=workspace_root / "pathflow_guard.db",
        requests_dir=workspace_root / "requests",
        manifests_dir=workspace_root / "manifests",
        accepted_dir=workspace_root / "accepted",
        review_dir=workspace_root / "review",
        rejected_dir=workspace_root / "rejected",
        audit_dir=workspace_root / "audit",
    )


def ensure_workspace(paths: WorkspacePaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.requests_dir.mkdir(parents=True, exist_ok=True)
    paths.manifests_dir.mkdir(parents=True, exist_ok=True)
    paths.accepted_dir.mkdir(parents=True, exist_ok=True)
    paths.review_dir.mkdir(parents=True, exist_ok=True)
    paths.rejected_dir.mkdir(parents=True, exist_ok=True)
    paths.audit_dir.mkdir(parents=True, exist_ok=True)
