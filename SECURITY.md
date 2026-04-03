# Security Policy

## Scope

PathFlow Guard is workflow-support software for pathology QC ingestion. Security issues should be treated as patient-safety-adjacent until triaged.

## Supported Versions

| Version | Supported |
| --- | --- |
| `0.2.x` | Yes |
| `0.1.x` | No |
| `< 0.1.0` | No |

## Principles

- minimize PHI exposure
- use deterministic artifact integrity checks
- fail closed on corrupted packages
- require reviewed changes through CI/CD

## Reporting

Use GitHub's private vulnerability reporting flow on the canonical repository Security tab.

- Do not open a public issue for a suspected vulnerability before maintainers confirm the exposure.
- Include the affected version, deployment surface, reproduction steps, operational impact, and any patient-safety or PHI implications.
- If the report concerns a packaged Windows release, include the release tag or artifact checksum from `SHA256SUMS.txt`.

## Response Expectations

- Initial triage target: within 5 business days
- Fix or mitigation target for confirmed high-severity issues: next patch release or faster when feasible
- Coordinated disclosure after a fix is available or a mitigation has been published
