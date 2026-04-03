# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and the project follows Semantic Versioning for GitHub releases.

## [Unreleased]

## [0.2.0] - 2026-04-03

### Added

- Windows release automation with packaged executable smoke tests and GitHub Release artifacts
- Runtime `doctor` command for source installs and packaged builds
- Per-job audit JSON export in the workspace audit directory
- Comprehensive GitHub-facing product documentation, including a richer README and illustrated HTML manual
- Local release assembly workflow with deterministic release notes and checksum generation

### Changed

- CI now installs the Python package with its development dependencies before linting and tests
- Python verification now includes CLI and web smoke coverage
- Quality and release documentation now match the current shipped implementation
- Release engineering now aligns packaged assets, checksums, and changelog-backed notes around one versioned release process

## [0.1.0] - 2026-04-03

### Added

- Python orchestrator with CLI, SQLite persistence, deterministic decisioning, local dashboard, and JSON API
- Raster and OpenSlide-backed metric extraction
- Windows PyInstaller packaging flow for `PathFlowGuard.exe`
- Companion C++ and Rust modules with CI coverage
- Regulated-development quality documentation and Azure deployment scaffolding
