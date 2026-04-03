# Architecture

## Goal

Catch low-quality digital pathology slides at the edge before they create cloud cost, downstream AI failure, or delayed review.

## End-To-End Flow

1. A scanner or lab workflow exports a whole-slide image and basic acquisition metadata.
2. The Python orchestrator extracts local metrics such as focus score, tissue coverage, and artifact ratio from raster tiles or OpenSlide-backed representative regions.
3. The Python orchestrator applies deterministic review thresholds and creates a job decision:
   - `accept`: upload and register the slide
   - `review`: hold for technologist review
   - `reject`: request rescan before cloud ingestion
4. The Python orchestrator writes a deterministic BLAKE2b manifest, persists audit events, and stages the package into the routed workspace lane.
5. In a cloud deployment, accepted jobs can be published to storage and a queue for downstream indexing or AI pipelines.
6. Every decision is logged with enough detail for CAPA, trending, and design-history evidence.

## Why This Split

- Python owns the current shipping workflow policy, metric extraction, manifests, audit events, and integration code.
- C++ provides a native reference path for future performance benchmarking and hardening.
- Rust provides a companion integrity tool for deterministic manifest verification and future hardening.
- Azure owns queueing, object storage, secrets, and audit-friendly deployment surfaces.

## Intended Deployment

### Edge

- Scanner-adjacent worker service
- Local encrypted staging volume
- QC calculation near the instrument network
- Optional companion attestor on the same node or adjacent gateway

### Cloud

- Azure Storage for slide packages and manifests
- Azure Service Bus for job distribution
- Azure Container Apps for stateless Python orchestration APIs and workers
- Azure Key Vault for secrets and signing material

## Reliability Posture

- Fail closed on corrupt manifests
- Fail safe on borderline QC results by routing to manual review instead of auto-accept
- Idempotent ingestion keyed by `slide_id` plus content hash
- Structured audit trail for every decision

## Security Posture

- PHI minimization in logs
- integrity manifests for upload packages
- least-privilege cloud identities
- branch protection and mandatory review in CI/CD
- explicit dependency and static-analysis gates in CI
