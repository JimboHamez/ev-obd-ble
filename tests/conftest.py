"""Shared fixtures for the integration test suite.

The helpers here deliberately discover the integration package at runtime
instead of hard-coding its name, so the suite keeps working across the
rename from the Nissan Leaf domain to the bZ4X / Solterra one.
"""

import contextlib
import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_ROOT = REPO_ROOT / "custom_components"

# Modules eagerly imported below. Keep in step with the package contents.
INTEGRATION_MODULES = (
    "const",
    "entity",
    "coordinator",
    "overrides",
    "sensor",
    "binary_sensor",
    "button",
    "config_flow",
    "__init__",
)


def _discover_integration_dir() -> Path:
    """Return the single integration directory under custom_components/."""
    candidates = [path for path in COMPONENTS_ROOT.iterdir() if path.is_dir() and (path / "manifest.json").is_file()]
    if len(candidates) != 1:
        raise AssertionError(
            f"expected exactly one integration under {COMPONENTS_ROOT}, found {[c.name for c in candidates]}"
        )
    return candidates[0]


INTEGRATION_DIR = _discover_integration_dir()
DOMAIN = INTEGRATION_DIR.name


def _preimport() -> None:
    """Import the integration package before any Home Assistant fixture runs.

    Home Assistant's ``hass`` fixture points ``config_dir`` at a temporary
    directory and prepends it to ``sys.path``. Its loader then imports
    ``custom_components`` from there, so that name resolves to the temp dir
    for the rest of the session and this repo's package becomes unreachable
    by name. Importing first puts our modules in ``sys.modules``, where later
    ``import_module`` calls find them regardless of what shadows the parent.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    for module in INTEGRATION_MODULES:
        # Let test_manifest.py report the failure with a useful message
        # rather than aborting collection of the whole suite.
        with contextlib.suppress(ImportError):
            importlib.import_module(f"custom_components.{DOMAIN}.{module}")


_preimport()


@pytest.fixture(scope="session")
def integration_dir() -> Path:
    """Path to the integration package directory."""
    return INTEGRATION_DIR


@pytest.fixture(scope="session")
def manifest() -> dict:
    """Parsed manifest.json of the integration."""
    return json.loads((INTEGRATION_DIR / "manifest.json").read_text())


@pytest.fixture
def custom_integration(enable_custom_integrations):
    """Let Home Assistant load this repo's integration by domain.

    Opt in only from tests that set up a real config entry; plain unit tests
    do not need it.
    """
    return
