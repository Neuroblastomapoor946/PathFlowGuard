# Code Review Standard

## Minimum Rules

- No direct merge to `main`
- At least one human reviewer on every production change
- CI must pass before merge
- Changes affecting behavior must update tests
- Changes affecting requirements or safety posture must update risk and traceability documents

## Reviewer Focus

- correctness
- failure handling
- performance regressions
- PHI and secret handling
- rollback and operability

## Security Expectations

- avoid unsafe parsing of untrusted input
- pin or review dependencies
- prefer deterministic outputs for audit-relevant components
- document any security tradeoff in the PR

