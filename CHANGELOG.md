# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Entries before this
file was added are in the GitHub releases of the upstream Nissan Leaf project.

## [Unreleased]

### Changed
- Tooling now matches the maintainer's other Home Assistant integrations: all
  configuration lives in `pyproject.toml`, test dependencies in
  `requirements_test.txt`, and CI runs pytest, ruff (format and lint) and
  strict mypy, plus hassfest, HACS validation and report-only security scans.
- `quality_scale.yaml` records the status of every quality scale rule against
  the Platinum target.
- `hacs.json` declares the minimum Home Assistant version (2026.2.0) and drops
  the `iot_class` key, which HACS does not accept there.

### Removed
- `setup.cfg`, `requirements-dev.txt` and `.pre-commit-config.yaml`. The
  pre-commit hooks ran black at 88 columns, which fought the 120-column ruff
  format this repo standardises on.
