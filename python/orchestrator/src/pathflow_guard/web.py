from __future__ import annotations

import html
import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import WorkspacePaths
from .database import JobRepository
from .models import SlideIngestionRequest, StoredJobRecord
from .pipeline import IngestionPipeline


class PathFlowGuardServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        workspace: WorkspacePaths,
        repository: JobRepository,
        pipeline: IngestionPipeline,
    ) -> None:
        super().__init__(server_address, PathFlowGuardRequestHandler)
        self.workspace = workspace
        self.repository = repository
        self.pipeline = pipeline


class PathFlowGuardRequestHandler(BaseHTTPRequestHandler):
    server: PathFlowGuardServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._respond_html(_render_dashboard(self.server.repository))
            return

        if parsed.path.startswith("/jobs/"):
            job_id = parsed.path.removeprefix("/jobs/")
            record = self.server.repository.get_job(job_id)
            if record is None:
                self._respond_not_found()
                return
            self._respond_html(_render_job_detail(record))
            return

        if parsed.path == "/api/jobs":
            payload = self.server.repository.export_jobs()
            self._respond_json(payload)
            return

        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.removeprefix("/api/jobs/")
            record = self.server.repository.get_job(job_id)
            if record is None:
                self._respond_not_found()
                return
            self._respond_json(asdict(record))
            return

        if parsed.path == "/healthz":
            self._respond_json({"status": "ok"})
            return

        self._respond_not_found()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/ingest":
            self._respond_not_found()
            return

        try:
            form = self._read_form()
            request = SlideIngestionRequest.from_mapping(
                {
                    "case_id": form.get("case_id", ""),
                    "slide_id": form.get("slide_id", ""),
                    "site_id": form.get("site_id", ""),
                    "objective_power": form.get("objective_power", 40),
                    "file_bytes": form.get("file_bytes", 0),
                    "focus_score": form.get("focus_score", 0),
                    "tissue_coverage": form.get("tissue_coverage", 0),
                    "artifact_ratio": form.get("artifact_ratio", 0),
                    "package_path": form.get("package_path"),
                    "notes": form.get("notes", ""),
                }
            )
            record = self.server.pipeline.ingest_request(request)
        except (FileNotFoundError, ValueError, KeyError) as error:
            self._respond_bad_request(str(error))
            return

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/jobs/{record.job_id}")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(data, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def _respond_html(self, document: str) -> None:
        encoded = document.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _respond_json(self, payload: object) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _respond_not_found(self) -> None:
        encoded = b"Not Found"
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _respond_bad_request(self, message: str) -> None:
        document = _page(
            "Bad Request",
            f"""
            <section class="panel">
              <h1>Invalid ingest request</h1>
              <p>{html.escape(message)}</p>
              <p><a href="/">Back to dashboard</a></p>
            </section>
            """,
        )
        encoded = document.encode("utf-8")
        self.send_response(HTTPStatus.BAD_REQUEST)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def serve(
    *,
    host: str,
    port: int,
    workspace: WorkspacePaths,
    repository: JobRepository,
    pipeline: IngestionPipeline,
) -> None:
    pipeline.initialize()
    server = PathFlowGuardServer((host, port), workspace, repository, pipeline)
    print(f"PathFlow Guard running on http://{host}:{port}")
    print(f"Workspace: {workspace.root}")
    server.serve_forever()


def _render_dashboard(repository: JobRepository) -> str:
    summary = repository.summarize()
    jobs = repository.list_jobs(limit=20)
    cards = "".join(
        [
            _metric_card("Total", str(summary.get("total", 0))),
            _metric_card("Accepted", str(summary.get("accept", 0))),
            _metric_card("Review", str(summary.get("review", 0))),
            _metric_card("Rejected", str(summary.get("reject", 0))),
        ]
    )
    rows = "".join(_job_row(job) for job in jobs) or (
        "<tr><td colspan='6'>No jobs yet. Use the form below to ingest one.</td></tr>"
    )
    body = f"""
    <section class="hero">
      <div>
        <p class="eyebrow">PathFlow Guard</p>
        <h1>Digital Pathology QC Control Room</h1>
        <p class="lede">
          Evaluate scan quality, generate audit records, and route packages into accept,
          review, or reject lanes before cloud ingestion.
        </p>
      </div>
      <div class="cards">{cards}</div>
    </section>
    <section class="panel">
      <h2>Recent Jobs</h2>
      <table>
        <thead>
          <tr>
            <th>Job</th>
            <th>Case</th>
            <th>Decision</th>
            <th>Focus</th>
            <th>Artifacts</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    <section class="panel">
      <h2>Manual Ingest</h2>
      <form method="post" action="/ingest" class="ingest-form">
        {_form_field("case_id", "Case ID", "CASE-2026-010")}
        {_form_field("slide_id", "Slide ID", "SLIDE-010")}
        {_form_field("site_id", "Site ID", "SITE-EDGE-01")}
        {_form_field("objective_power", "Objective Power", "40", field_type="number")}
        {_form_field("file_bytes", "File Size (bytes)", "", field_type="number", placeholder="Optional if package path is set")}
        {_form_field("focus_score", "Focus Score", "", field_type="number", step="0.1", placeholder="Optional if extracted from tiles")}
        {_form_field("tissue_coverage", "Tissue Coverage", "", field_type="number", step="0.01", placeholder="Optional if extracted from tiles")}
        {_form_field("artifact_ratio", "Artifact Ratio", "", field_type="number", step="0.01", placeholder="Optional if extracted from tiles")}
        {_form_field("package_path", "Package Path", "", placeholder="Optional directory or file path")}
        {_form_field("notes", "Notes", "", placeholder="Optional operational note")}
        <button type="submit">Ingest Slide</button>
      </form>
    </section>
    """
    return _page("PathFlow Guard", body)


def _render_job_detail(record: StoredJobRecord) -> str:
    request = record.request
    audit_record_path = _audit_record_path(record)
    reasons = "".join(f"<li>{html.escape(reason)}</li>" for reason in record.reasons) or "<li>none</li>"
    body = f"""
    <section class="hero compact">
      <div>
        <p class="eyebrow">Job Detail</p>
        <h1>{html.escape(record.job_id)}</h1>
        <p class="lede">Decision: <strong>{html.escape(record.decision.value)}</strong></p>
      </div>
      <div class="cards">
        {_metric_card("Focus", f"{request.focus_score:.1f}")}
        {_metric_card("Tissue", f"{request.tissue_coverage:.2f}")}
        {_metric_card("Artifacts", f"{request.artifact_ratio:.2f}")}
      </div>
    </section>
    <section class="panel details">
      <h2>Request</h2>
      <dl>
        <dt>Case ID</dt><dd>{html.escape(request.case_id)}</dd>
        <dt>Slide ID</dt><dd>{html.escape(request.slide_id)}</dd>
        <dt>Site ID</dt><dd>{html.escape(request.site_id)}</dd>
        <dt>Objective Power</dt><dd>{request.objective_power}</dd>
        <dt>File Bytes</dt><dd>{request.file_bytes}</dd>
        <dt>Package Path</dt><dd>{html.escape(request.package_path or "")}</dd>
        <dt>Stored Package Path</dt><dd>{html.escape(record.stored_package_path or "")}</dd>
        <dt>Manifest Path</dt><dd>{html.escape(record.manifest_path or "")}</dd>
        <dt>Audit Record</dt><dd>{html.escape(audit_record_path)}</dd>
        <dt>Request Record</dt><dd>{html.escape(record.request_record_path)}</dd>
        <dt>Notes</dt><dd>{html.escape(request.notes)}</dd>
        <dt>Created</dt><dd>{html.escape(record.created_at)}</dd>
      </dl>
      <h2>Reason Codes</h2>
      <ul>{reasons}</ul>
      <p><a href="/">Back to dashboard</a></p>
    </section>
    """
    return _page(f"Job {record.job_id}", body)


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f3efe8;
      --panel: #fffdf8;
      --ink: #1b1f23;
      --muted: #5a6570;
      --line: #d7cfc3;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --warn: #b45309;
      --danger: #b91c1c;
      --shadow: 0 18px 40px rgba(20, 18, 12, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Aptos", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 30%),
        linear-gradient(180deg, #f8f4ee 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 24px;
      align-items: start;
      margin-bottom: 24px;
    }}
    .hero.compact {{
      grid-template-columns: 1fr;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--accent-dark);
      font-size: 12px;
      font-weight: 700;
      margin: 0 0 12px;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3.4rem); line-height: 0.95; }}
    .lede {{
      max-width: 65ch;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.6;
      margin: 0;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
    }}
    .card {{
      padding: 18px;
    }}
    .card .label {{
      font-size: 0.8rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .card .value {{
      margin-top: 8px;
      font-size: 1.8rem;
      font-weight: 700;
    }}
    .panel {{
      padding: 20px;
      margin-top: 20px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
    }}
    th, td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .pill.accept {{ background: rgba(15, 118, 110, 0.14); color: var(--accent-dark); }}
    .pill.review {{ background: rgba(180, 83, 9, 0.16); color: var(--warn); }}
    .pill.reject {{ background: rgba(185, 28, 28, 0.12); color: var(--danger); }}
    .ingest-form {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .field {{
      display: grid;
      gap: 6px;
    }}
    label {{
      font-size: 0.88rem;
      color: var(--muted);
    }}
    input {{
      width: 100%;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: white;
      font: inherit;
    }}
    button {{
      padding: 14px 18px;
      border: 0;
      border-radius: 12px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      align-self: end;
    }}
    .details dl {{
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 10px 16px;
      margin: 0 0 18px;
    }}
    .details dt {{
      color: var(--muted);
      font-weight: 600;
    }}
    a {{ color: var(--accent-dark); }}
    @media (max-width: 820px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .details dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>{body}</main>
</body>
</html>"""


def _metric_card(label: str, value: str) -> str:
    return f"""
    <article class="card">
      <div class="label">{html.escape(label)}</div>
      <div class="value">{html.escape(value)}</div>
    </article>
    """


def _job_row(job: StoredJobRecord) -> str:
    return f"""
    <tr>
      <td><a href="/jobs/{html.escape(job.job_id)}">{html.escape(job.job_id)}</a></td>
      <td>{html.escape(job.request.case_id)}</td>
      <td><span class="pill {html.escape(job.decision.value)}">{html.escape(job.decision.value)}</span></td>
      <td>{job.request.focus_score:.1f}</td>
      <td>{job.request.artifact_ratio:.2f}</td>
      <td>{html.escape(job.created_at)}</td>
    </tr>
    """


def _audit_record_path(record: StoredJobRecord) -> str:
    request_record_path = Path(record.request_record_path)
    workspace_root = request_record_path.parent.parent
    audit_path = workspace_root / "audit" / f"{record.job_id}.json"
    return str(audit_path) if audit_path.exists() else ""


def _form_field(
    name: str,
    label: str,
    value: str,
    *,
    field_type: str = "text",
    step: str | None = None,
    placeholder: str | None = None,
) -> str:
    step_attr = f' step="{html.escape(step)}"' if step is not None else ""
    placeholder_attr = (
        f' placeholder="{html.escape(placeholder)}"' if placeholder is not None else ""
    )
    return f"""
    <div class="field">
      <label for="{html.escape(name)}">{html.escape(label)}</label>
      <input
        id="{html.escape(name)}"
        name="{html.escape(name)}"
        type="{html.escape(field_type)}"
        value="{html.escape(value)}"{step_attr}{placeholder_attr}>
    </div>
    """
