"""Behavioural tests for the update coordinator.

The coordinator holds the polling-interval state machine and the value cache.
Both are vehicle-independent, so these tests stay valid across the conversion
and act as the regression net while the command set is swapped out.
"""

import importlib
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

ADDRESS = "AA:BB:CC:DD:EE:FF"


def _coordinator_module(integration_dir: Path):
    return importlib.import_module(f"custom_components.{integration_dir.name}.coordinator")


def _make_coordinator(hass: HomeAssistant, integration_dir: Path, options, api):
    module = _coordinator_module(integration_dir)
    cls = next(
        value
        for name, value in vars(module).items()
        if name.endswith("DataUpdateCoordinator") and isinstance(value, type) and value.__module__ == module.__name__
    )
    return cls(hass, address=ADDRESS, api=api, options=options)


@pytest.fixture
def api():
    """A stand-in for the OBD BLE API client."""
    return AsyncMock()


def _present(integration_dir: Path, value: bool):
    return patch(
        f"custom_components.{integration_dir.name}.coordinator.async_address_present",
        return_value=value,
    )


async def test_car_on_uses_fast_poll(hass: HomeAssistant, integration_dir: Path, api):
    """Data returned means the car is awake: poll at the fast interval."""
    api.async_get_data.return_value = {"state_of_charge": 82.0}
    coordinator = _make_coordinator(hass, integration_dir, {"fast_poll": 7}, api)

    with _present(integration_dir, True):
        data = await coordinator._async_update_data()

    assert data == {"state_of_charge": 82.0}
    assert coordinator.update_interval == timedelta(seconds=7)


async def test_car_off_uses_slow_poll(hass: HomeAssistant, integration_dir: Path, api):
    """An empty response means the car is off: back off to the slow interval."""
    api.async_get_data.return_value = {}
    coordinator = _make_coordinator(hass, integration_dir, {"slow_poll": 111}, api)

    with _present(integration_dir, True):
        await coordinator._async_update_data()

    assert coordinator.update_interval == timedelta(seconds=111)


async def test_out_of_range_uses_extra_slow_poll(hass: HomeAssistant, integration_dir: Path, api):
    """No BLE advertisement means out of range: back off the furthest."""
    coordinator = _make_coordinator(hass, integration_dir, {"xs_poll": 999}, api)

    with _present(integration_dir, False):
        data = await coordinator._async_update_data()

    assert data == {}
    assert coordinator.update_interval == timedelta(seconds=999)
    api.async_get_data.assert_not_awaited()


async def test_cache_survives_out_of_range(hass: HomeAssistant, integration_dir: Path, api):
    """With caching on, values read while in range persist once out of range."""
    api.async_get_data.return_value = {"state_of_charge": 64.0}
    coordinator = _make_coordinator(hass, integration_dir, {"cache_values": True}, api)

    with _present(integration_dir, True):
        await coordinator._async_update_data()
    with _present(integration_dir, False):
        data = await coordinator._async_update_data()

    assert data == {"state_of_charge": 64.0}


async def test_cache_merges_partial_reads(hass: HomeAssistant, integration_dir: Path, api):
    """A later poll that reads fewer PIDs must not drop earlier values."""
    coordinator = _make_coordinator(hass, integration_dir, {"cache_values": True}, api)

    api.async_get_data.return_value = {"state_of_charge": 64.0, "odometer": 12345}
    with _present(integration_dir, True):
        await coordinator._async_update_data()

    api.async_get_data.return_value = {"state_of_charge": 63.5}
    with _present(integration_dir, True):
        data = await coordinator._async_update_data()

    assert data == {"state_of_charge": 63.5, "odometer": 12345}


async def test_failed_connection_raises_update_failed(hass: HomeAssistant, integration_dir: Path, api):
    """A None response from the API is a connection failure, not empty data."""
    api.async_get_data.return_value = None
    coordinator = _make_coordinator(hass, integration_dir, {}, api)

    with _present(integration_dir, True), pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_fetch_timeout_raises_update_failed(hass: HomeAssistant, integration_dir: Path, api):
    """A BLE read that overruns the timeout must not wedge the coordinator."""
    api.async_get_data.side_effect = TimeoutError
    coordinator = _make_coordinator(hass, integration_dir, {"fetch_timeout": 1}, api)

    with _present(integration_dir, True), pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
