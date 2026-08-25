"""Consistency checks over the integration's metadata.

These guard the rename: the domain, the package directory, the HACS name and
the version are stated in several places and must not drift apart.
"""

import importlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

MODULES = (
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


def test_domain_matches_package_directory(integration_dir: Path, manifest: dict):
    """manifest.json domain must equal the package directory name."""
    assert manifest["domain"] == integration_dir.name


def test_const_domain_matches_manifest(integration_dir: Path, manifest: dict):
    """const.DOMAIN must equal the manifest domain."""
    const = importlib.import_module(f"custom_components.{integration_dir.name}.const")
    assert const.DOMAIN == manifest["domain"]


def test_const_version_matches_manifest(integration_dir: Path, manifest: dict):
    """const.VERSION must equal the manifest version."""
    const = importlib.import_module(f"custom_components.{integration_dir.name}.const")
    assert const.VERSION == manifest["version"]


def test_const_name_matches_manifest_and_hacs(integration_dir: Path, manifest: dict):
    """The display name must be identical in const.py, manifest.json and hacs.json."""
    const = importlib.import_module(f"custom_components.{integration_dir.name}.const")
    hacs = json.loads((REPO_ROOT / "hacs.json").read_text())
    assert const.NAME == manifest["name"] == hacs["name"]


def test_override_paths_point_at_this_integration(integration_dir: Path):
    """OVERRIDES_FILE / DECODERS_MODULE_FILE must reference the current domain."""
    const = importlib.import_module(f"custom_components.{integration_dir.name}.const")
    for path in (const.OVERRIDES_FILE, const.DECODERS_MODULE_FILE):
        assert path.startswith(f"custom_components/{integration_dir.name}/"), path


def test_manifest_requirements_are_installed(manifest: dict):
    """Every manifest requirement must be importable in the dev environment."""
    for requirement in manifest.get("requirements", []):
        distribution = requirement.split(">=")[0].split("==")[0].split("<")[0].strip()
        module = distribution.replace("-", "_")
        pytest.importorskip(
            module,
            reason=f"{distribution} missing; run pip install -r requirements-dev.txt",
        )


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(integration_dir: Path, module: str):
    """Every module of the integration must import cleanly."""
    importlib.import_module(f"custom_components.{integration_dir.name}.{module}")


def test_platform_modules_exist(integration_dir: Path):
    """Every platform listed in const.PLATFORMS must have a matching module."""
    const = importlib.import_module(f"custom_components.{integration_dir.name}.const")
    for platform in const.PLATFORMS:
        assert (integration_dir / f"{platform.value}.py").is_file(), platform


def test_translations_match_strings(integration_dir: Path):
    """translations/en.json must expose the same keys as strings.json."""
    strings = json.loads((integration_dir / "strings.json").read_text())
    english = json.loads((integration_dir / "translations" / "en.json").read_text())

    def keys(node, prefix=""):
        if not isinstance(node, dict):
            return {prefix}
        return {
            k for key, value in node.items() for k in keys(value, f"{prefix}/{key}")
        }

    assert keys(strings) == keys(english)
