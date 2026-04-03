# Traceability Matrix

| Requirement | Description | Implementation | Verification |
| --- | --- | --- | --- |
| SYS-001 | The system shall classify slide jobs as accept, review, or reject. | `python/orchestrator/src/pathflow_guard/service.py` | `python/orchestrator/tests/test_service.py` |
| SYS-002 | The system shall include reason codes in every decision. | `python/orchestrator/src/pathflow_guard/service.py` | `python/orchestrator/tests/test_service.py` |
| SYS-003 | The system shall compute QC metrics from raster tiles or OpenSlide samples when requests omit them. | `python/orchestrator/src/pathflow_guard/imaging.py`, `python/orchestrator/src/pathflow_guard/pipeline.py` | `python/orchestrator/tests/test_imaging.py`, `python/orchestrator/tests/test_pipeline.py`, `python/orchestrator/tests/test_cli.py` |
| SYS-004 | The system shall generate deterministic BLAKE2b manifests for artifact packages. | `python/orchestrator/src/pathflow_guard/manifest.py` | `python/orchestrator/tests/test_manifest.py` |
| SYS-005 | The system shall expose runtime diagnostics for source installs and packaged builds. | `python/orchestrator/src/pathflow_guard/cli.py`, `python/orchestrator/src/pathflow_guard/imaging.py` | `python/orchestrator/tests/test_cli.py`, `.github/workflows/ci.yml`, `.github/workflows/release.yml` |
| SYS-006 | The system shall gate merges and releases with automated checks. | `.github/workflows/ci.yml`, `.github/workflows/release.yml` | GitHub Actions run history |
| SYS-007 | The repository shall maintain a native QC reference module for future benchmarking and hardening. | `cpp/qc-core/src/qc_metrics.cpp` | `cpp/qc-core/tests/qc_metrics_tests.cpp` |
| SYS-008 | The repository shall include a companion integrity attestor for deterministic manifest verification. | `rust/attestor/src/main.rs` | `rust/attestor/src/main.rs` unit tests |
| SYS-009 | The system shall maintain linked quality artifacts for risk and lifecycle evidence. | `docs/quality/*` | design-review process |
