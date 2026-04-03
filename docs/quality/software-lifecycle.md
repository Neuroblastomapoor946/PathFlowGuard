# Software Lifecycle

This project uses an IEC 62304-style decomposition even though it remains pre-validation workflow-support software rather than a regulatory submission.

## Software Item Decomposition

- Item A: Python orchestration and decision engine
- Item B: C++ QC metrics library
- Item C: Rust attestation sidecar
- Item D: Cloud deployment and infrastructure glue

## Preliminary Safety Position

Initial working assumption: treat the workflow-support software as requiring at least Class B rigor until a formal hazard analysis proves otherwise.

Reasoning:

- Incorrect accept/reject decisions may delay review, trigger unnecessary rescans, or route poor-quality images into downstream analytics.
- The first implementation does not make or display a diagnostic call. It supports workflow control and quality gating.

## Lifecycle Activities

### Development Planning

- Repository standards in place
- CI gates defined
- pull-request checklist established
- requirements, risks, and verification traceability documented

### Requirements Analysis

See [traceability-matrix.md](traceability-matrix.md).

### Architecture And Detailed Design

See [../architecture.md](../architecture.md).

### Implementation

- narrow, testable modules by language boundary
- deterministic rules for first release
- explicit type modeling for decision records

### Verification

- Python unit tests for decision logic
- Python CLI and web smoke tests for the operator-facing runtime
- C++ unit tests for tile metrics
- Rust tests for manifest generation determinism
- CI executes all available language-level tests
- Windows release automation smoke-tests the packaged executable before publishing GitHub artifacts

### Problem Resolution

Recommended process for a full project:

1. log issue with severity and potential safety impact
2. assess whether risk file and requirements need updates
3. implement fix under reviewed PR
4. attach verification evidence
5. close with traceability reference
