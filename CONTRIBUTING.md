# Development setup

## Requirements

Python 3.13 (matching the version Home Assistant 2026.2 ships against).

## Install

```bash
pip install -r requirements_test.txt
```

`requirements_test.txt` includes the integration's own runtime requirement from
`manifest.json`, so the test suite can import the package directly. All tool
configuration (pytest, coverage, ruff, mypy) lives in `pyproject.toml`.

> On a Debian/Ubuntu host with an externally-managed Python, add
> `--break-system-packages`, or work inside a virtualenv.

## Test

```bash
pytest                    # with coverage, per pyproject.toml
pytest --no-cov           # faster
ruff format --check .
ruff check .
mypy custom_components    # strict; the quality scale's strict-typing rule
```

CI runs the same checks (`.github/workflows/test.yml`), plus hassfest, HACS
validation and report-only security scans. `quality_scale.yaml` in the
integration package records the status of every quality scale rule; update it
in the same change that closes or opens a rule.

## How the test suite is laid out

- `tests/conftest.py` — discovers the integration under `custom_components/`
  rather than hard-coding its domain, so the suite survives the rename.
- `tests/test_manifest.py` — metadata consistency: the domain, name and
  version must agree across `manifest.json`, `hacs.json` and `const.py`; every
  module must import; every platform in `const.PLATFORMS` must have a module;
  `translations/en.json` must match `strings.json`.
- `tests/test_coordinator.py` — the polling state machine and value cache.

### Two things to know before adding tests

**The integration package is imported eagerly at conftest load.** Home
Assistant's `hass` fixture points `config_dir` at a temp directory and
prepends it to `sys.path`; its loader then imports `custom_components` from
there, which shadows this repo's package for the rest of the session.
Pre-importing puts our modules in `sys.modules` first, where later
`import_module` calls still find them. If you add a module to the integration,
add it to `INTEGRATION_MODULES` in `conftest.py`.

**`enable_custom_integrations` is opt-in, via the `custom_integration`
fixture.** It is not autouse for the same reason. Request it only from tests
that set up a real config entry through Home Assistant.

## Porting work

See [CONVERSION.md](CONVERSION.md) for the state of the bZ4X / Solterra port
and the open decisions.
