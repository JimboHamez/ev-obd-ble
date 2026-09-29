"""Checks for the quality scale rules this repo commits to.

The integration targets Platinum, so these rules are a definition of done
rather than a periodic audit. The checks here are the cheap, static subset:
they guard against a rule being silently dropped when platforms are added or
rewritten during the conversion. Like the rest of the suite, they discover the
integration package rather than hard-coding its domain.
"""

import ast
import importlib
import json
from pathlib import Path

import pytest

PLATFORM_MODULES = ("binary_sensor", "button", "sensor")


def _module(integration_dir: Path, name: str):
    return importlib.import_module(f"custom_components.{integration_dir.name}.{name}")


def _source(integration_dir: Path, name: str) -> str:
    return (integration_dir / f"{name}.py").read_text()


def test_py_typed_marker_present(integration_dir: Path) -> None:
    """strict-typing: the package must be PEP-561 compliant."""
    assert (integration_dir / "py.typed").is_file()


@pytest.mark.parametrize("platform", PLATFORM_MODULES)
def test_platform_declares_parallel_updates(integration_dir: Path, platform: str) -> None:
    """parallel-updates: every entity platform declares its limit."""
    module = _module(integration_dir, platform)
    assert isinstance(getattr(module, "PARALLEL_UPDATES", None), int)


def test_base_entity_has_entity_name(integration_dir: Path) -> None:
    """has-entity-name: names are composed from the device name.

    Read from the source rather than the class: Home Assistant's entity
    metaclass rewrites ``_attr_`` class attributes into cached properties, so
    the assigned value is not readable off the class object.
    """
    tree = ast.parse(_source(integration_dir, "entity"))
    assigned = {
        target.id: node.value
        for klass in tree.body
        if isinstance(klass, ast.ClassDef)
        for node in klass.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    declared = assigned.get("_attr_has_entity_name")
    assert isinstance(declared, ast.Constant) and declared.value is True


@pytest.mark.parametrize("platform", PLATFORM_MODULES)
def test_no_raw_entity_names(integration_dir: Path, platform: str) -> None:
    """has-entity-name: entity names come from translations, not raw strings."""
    tree = ast.parse(_source(integration_dir, platform))
    assigned = {
        target.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Attribute)
    }
    assert "_attr_name" not in assigned


@pytest.mark.parametrize("platform", PLATFORM_MODULES)
def test_platform_reads_runtime_data(integration_dir: Path, platform: str) -> None:
    """runtime-data: platforms take the coordinator off the config entry."""
    source = _source(integration_dir, platform)
    assert "entry.runtime_data" in source
    assert "hass.data" not in source


def test_setup_stores_coordinator_in_runtime_data(integration_dir: Path) -> None:
    """runtime-data: setup must not stash the coordinator in hass.data."""
    source = _source(integration_dir, "__init__")
    assert "entry.runtime_data = " in source
    assert "hass.data" not in source


@pytest.mark.parametrize("translations", ["strings.json", "translations/en.json"])
def test_translation_keys_resolve(integration_dir: Path, translations: str) -> None:
    """entity-translations: every translation_key has a name, and vice versa."""
    entity_names = json.loads((integration_dir / translations).read_text())["entity"]

    for platform in PLATFORM_MODULES:
        tree = ast.parse(_source(integration_dir, platform))
        used = {
            keyword.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == "translation_key" and isinstance(keyword.value, ast.Constant)
        }
        declared = set(entity_names.get(platform, {}))
        assert used, f"{platform} declares no translation keys"
        assert used == declared, f"{platform}: {used ^ declared} missing from one side in {translations}"
