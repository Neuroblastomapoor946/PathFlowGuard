# Contributing

## Scope

PathFlow Guard is maintained as workflow-support software for digital pathology QC ingestion. Contributions should keep the current product position explicit: deterministic routing and operator review support, not autonomous diagnosis.

## Development Setup

From the repository root:

```powershell
cd python\orchestrator
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -e ".[dev]"
py -3.12 -m unittest discover -s tests -v
ruff check src tests
```

Companion modules:

```powershell
cargo test --manifest-path rust\attestor\Cargo.toml
cmake -S cpp\qc-core -B build\cpp
cmake --build build\cpp --config Release
ctest --test-dir build\cpp --build-config Release --output-on-failure
```

## Pull Requests

- Keep changes small enough to review clinically and operationally.
- Update tests with behavioral changes.
- Update `README.md`, `CHANGELOG.md`, and the quality docs when product claims or verification scope changes.
- Do not commit generated runtime folders, packaged executables, SQLite databases, or `__pycache__` outputs.

## Release Process

1. Update `CHANGELOG.md` and ensure the release version is aligned in:
   - `python/orchestrator/pyproject.toml`
   - `rust/attestor/Cargo.toml`
   - `SECURITY.md`
2. Build the release package locally when you want a pre-publish verification pass:

   ```powershell
   .\scripts\build_release.ps1 -Version X.Y.Z -Python "py -3.12"
   ```

3. Ensure CI is green on `main`.
4. Create and push a tag in the form `vX.Y.Z`.
5. GitHub Actions builds the Windows executable, runs packaged smoke tests, assembles release assets, and publishes the GitHub Release.
6. If code-signing secrets are configured, the release workflow signs `PathFlowGuard.exe` before publishing.

Optional release secrets for Windows signing:

- `WINDOWS_CERT_BASE64`: base64-encoded PFX certificate
- `WINDOWS_CERT_PASSWORD`: password for the PFX certificate

## Security Reports

Do not report vulnerabilities in public issues. Use the private GitHub Security reporting flow described in `SECURITY.md`.
