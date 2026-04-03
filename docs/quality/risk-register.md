# Risk Register

| ID | Hazard / Failure Mode | Potential Harm | Initial Control Strategy | Verification |
| --- | --- | --- | --- | --- |
| R-001 | Poor-quality slide incorrectly accepted | delayed diagnosis support workflow, failed downstream analysis, repeat manual work | conservative thresholds, manual-review state, audit logging | Python decision tests, validation dataset review |
| R-002 | Good slide incorrectly rejected | unnecessary rescan, delayed turnaround time | separate `review` band before `reject`, threshold tuning, trend monitoring | Python decision tests, acceptance criteria review |
| R-003 | Upload package tampering or corruption | broken traceability, data integrity loss | deterministic file hashes, audit records, signed or attestable manifests, fail-closed ingest | Python manifest tests, Rust manifest tests, Windows release checksum publication |
| R-004 | PHI leakage in logs or telemetry | privacy breach, compliance impact | pseudonymous IDs in orchestration records, structured logging policy, suppressed default HTTP access logging | code review checklist, Python web tests, packaged release smoke tests |
| R-005 | QC metric runtime too slow for scanner-side use | workflow bottleneck, operator bypass | bounded tile sampling, Python runtime smoke tests, C++ reference path for future optimization, benchmark requirement | Python imaging tests, CLI and packaged executable smoke tests, C++ metric tests; representative hardware benchmarks remain pending |
| R-006 | Cloud dependency outage or queue failure | ingestion backlog, lost work visibility | idempotent jobs, retry policy, local staging, queue dead-lettering | Python pipeline and web tests cover the local staging path; Azure outage testing depends on a deployed cloud environment |

## Residual-Risk Notes

- This implementation intentionally routes uncertainty to manual review rather than attempting fully autonomous acceptance.
- Final residual-risk acceptability would depend on real validation data and intended use.
