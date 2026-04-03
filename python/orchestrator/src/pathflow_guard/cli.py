from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

from .config import WorkspacePaths, build_workspace
from .database import JobRepository
from .imaging import extract_metrics_from_package, runtime_capabilities
from .models import SlideIngestionRequest
from .pipeline import IngestionPipeline, resolve_request_context
from .resources import application_root, samples_root
from .service import evaluate_request
from .web import serve


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if _is_legacy_evaluate_invocation(args):
        request_path = Path(args[0])
        request = _load_request(request_path)
        request, _, extracted_metrics = resolve_request_context(
            request,
            request_source_path=request_path.resolve(),
        )
        payload = {
            "request": asdict(request),
            "evaluation": asdict(evaluate_request(request)),
        }
        if extracted_metrics is not None:
            payload["extracted_metrics"] = asdict(extracted_metrics)
        print(json.dumps(payload, indent=2))
        return 0

    parser = _build_parser()
    namespace = parser.parse_args(args)
    if not hasattr(namespace, "handler"):
        parser.print_help()
        return 2

    return int(namespace.handler(namespace))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pathflow-guard",
        description="Executable local application for pathology QC ingestion and review routing.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create the workspace and database.")
    _add_workspace_argument(init_parser)
    init_parser.set_defaults(handler=_handle_init)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate a request JSON without writing to the workspace.",
    )
    evaluate_parser.add_argument("request_json", type=Path)
    evaluate_parser.set_defaults(handler=_handle_evaluate)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract QC metrics from a tile image file or directory.",
    )
    extract_parser.add_argument("package_path", type=Path)
    extract_parser.set_defaults(handler=_handle_extract)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Report runtime capabilities for source installs or packaged builds.",
    )
    doctor_parser.set_defaults(handler=_handle_doctor)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Evaluate a request JSON, persist it, and stage any package files.",
    )
    ingest_parser.add_argument("request_json", type=Path)
    _add_workspace_argument(ingest_parser)
    ingest_parser.set_defaults(handler=_handle_ingest)

    report_parser = subparsers.add_parser("report", help="Print decision counts and recent jobs.")
    _add_workspace_argument(report_parser)
    report_parser.add_argument("--limit", type=int, default=10)
    report_parser.set_defaults(handler=_handle_report)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run the local PathFlow Guard dashboard and API.",
    )
    _add_workspace_argument(serve_parser)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.set_defaults(handler=_handle_serve)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Seed the workspace with sample requests from the repository.",
    )
    _add_workspace_argument(demo_parser)
    demo_parser.set_defaults(handler=_handle_demo)

    return parser


def _handle_init(namespace: argparse.Namespace) -> int:
    workspace = _workspace_from_namespace(namespace)
    pipeline = _build_pipeline(workspace)
    pipeline.initialize()
    print(f"Initialized workspace at {workspace.root}")
    return 0


def _handle_evaluate(namespace: argparse.Namespace) -> int:
    request = _load_request(namespace.request_json)
    request, _, extracted_metrics = resolve_request_context(
        request,
        request_source_path=namespace.request_json.resolve(),
    )
    payload = {
        "request": asdict(request),
        "evaluation": asdict(evaluate_request(request)),
    }
    if extracted_metrics is not None:
        payload["extracted_metrics"] = asdict(extracted_metrics)
    print(json.dumps(payload, indent=2))
    return 0


def _handle_extract(namespace: argparse.Namespace) -> int:
    metrics = extract_metrics_from_package(namespace.package_path.resolve())
    print(json.dumps(asdict(metrics), indent=2))
    return 0


def _handle_doctor(namespace: argparse.Namespace) -> int:
    _ = namespace
    payload = {
        "application_root": str(application_root()),
        "samples_root": str(samples_root()),
        "samples_available": samples_root().exists(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "frozen": bool(getattr(sys, "frozen", False)),
        "runtime": runtime_capabilities(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _handle_ingest(namespace: argparse.Namespace) -> int:
    workspace = _workspace_from_namespace(namespace)
    pipeline = _build_pipeline(workspace)
    request = _load_request(namespace.request_json)
    record = pipeline.ingest_request(request, request_source_path=namespace.request_json.resolve())
    print(json.dumps(asdict(record), indent=2))
    return 0


def _handle_report(namespace: argparse.Namespace) -> int:
    workspace = _workspace_from_namespace(namespace)
    workspace.root.mkdir(parents=True, exist_ok=True)
    repository = JobRepository(workspace.db_path)
    repository.initialize()
    summary = repository.summarize()
    jobs = repository.list_jobs(limit=namespace.limit)
    payload = {
        "workspace": str(workspace.root),
        "summary": summary,
        "recent_jobs": [asdict(job) for job in jobs],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _handle_serve(namespace: argparse.Namespace) -> int:
    workspace = _workspace_from_namespace(namespace)
    repository = JobRepository(workspace.db_path)
    pipeline = IngestionPipeline(workspace, repository)
    serve(
        host=namespace.host,
        port=namespace.port,
        workspace=workspace,
        repository=repository,
        pipeline=pipeline,
    )
    return 0


def _handle_demo(namespace: argparse.Namespace) -> int:
    workspace = _workspace_from_namespace(namespace)
    pipeline = _build_pipeline(workspace)
    pipeline.initialize()
    sample_dir = samples_root() / "requests"
    if not sample_dir.exists():
        raise FileNotFoundError(f"Sample request directory not found: {sample_dir}")
    ingested = []
    for request_path in sorted(sample_dir.glob("*.json")):
        request = _load_request(request_path)
        ingested.append(
            asdict(pipeline.ingest_request(request, request_source_path=request_path.resolve()))
        )

    print(
        json.dumps(
            {
                "workspace": str(workspace.root),
                "seeded_jobs": ingested,
            },
            indent=2,
        )
    )
    return 0


def _workspace_from_namespace(namespace: argparse.Namespace) -> WorkspacePaths:
    root = getattr(namespace, "workspace", None)
    return build_workspace(root)


def _build_pipeline(workspace: WorkspacePaths) -> IngestionPipeline:
    repository = JobRepository(workspace.db_path)
    return IngestionPipeline(workspace, repository)


def _load_request(path: Path) -> SlideIngestionRequest:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SlideIngestionRequest.from_mapping(data)


def _add_workspace_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace directory for the database, manifests, and routed packages.",
    )


def _is_legacy_evaluate_invocation(args: list[str]) -> bool:
    return len(args) == 1 and Path(args[0]).exists()
