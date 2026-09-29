"""Coodinator for Nissan Leaf OBD BLE."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.bluetooth.api import async_address_present
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Mapping

    from py_nissan_leaf_obd_ble import NissanLeafObdBleApiClient
    from py_nissan_leaf_obd_ble.OBDCommand import OBDCommand

    from homeassistant.components.sensor import SensorEntityDescription
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# when the device is in range, and the car is on, poll quickly to get
# as much data as we can before it turns off
FAST_POLL_INTERVAL = timedelta(seconds=10)

# when the device is in range, but the car is off, we need to poll
# occasionally to see whether the car has be turned back on. On some cars
# this causes a relay to click every time, so this interval needs to be
# as long as possible to prevent excessive wear on the relay.
SLOW_POLL_INTERVAL = timedelta(minutes=5)

# when the device is out of range, use ultra slow polling since a bluetooth
# advertisement message will kick it back into life when back in range.
# see __init__.py: _async_specific_device_found()
ULTRA_SLOW_POLL_INTERVAL = timedelta(hours=1)

DEFAULT_FAST_POLL = 10  # pick sane defaults for your integration
DEFAULT_SLOW_POLL = 300
DEFAULT_XS_POLL = 3600
DEFAULT_CACHE_VALUES = True
# Cap BLE read duration so HA's request_refresh debouncer lock is not held forever;
# otherwise BLE advertisements trigger async_request_refresh() but it no-ops (~70ms).
DEFAULT_FETCH_TIMEOUT = 90


class NissanLeafObdBleDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        api: NissanLeafObdBleApiClient,
        options: Mapping[str, Any],
        extra_commands: dict[str, OBDCommand] | None = None,
        extra_sensor_descriptions: dict[str, SensorEntityDescription] | None = None,
        disabled_commands: set[str] | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=FAST_POLL_INTERVAL,
            always_update=True,
        )
        self._address = address
        self.api = api
        self._cache_data: dict[str, Any] = {}
        self.extra_commands = extra_commands or {}
        self.extra_sensor_descriptions = extra_sensor_descriptions or {}
        self.disabled_commands = disabled_commands or set()
        self.options = options

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""

        # Check if the device is still available
        _LOGGER.debug("Check if the device is still available to connect")
        available = async_address_present(self.hass, self._address, connectable=True)
        if not available:
            # Device out of range? Switch to active polling interval for when it reappears
            _LOGGER.debug("Car out of range? Switch to extra slow polling")
            self.update_interval = timedelta(seconds=self._xs_poll_interval)
            _LOGGER.debug(
                "Car out of range? Switch to ultra slow polling: interval = %s",
                self.update_interval,
            )
            if self.options.get("cache_values", False):
                return self._cache_data
            return {}

        try:
            # The OBD library ships no type information, so pin the shape here.
            new_data: dict[str, Any] | None = await asyncio.wait_for(
                self.api.async_get_data(
                    self.options,
                    extra_commands=self.extra_commands or None,
                    disabled_commands=self.disabled_commands or None,
                ),
                timeout=self._fetch_timeout,
            )
            if new_data is None:
                raise UpdateFailed("Failed to connect to OBD device")
            if len(new_data) == 0:
                # Car is probably off. Switch to slow polling inteval
                self.update_interval = timedelta(seconds=self._slow_poll_interval)
                _LOGGER.debug(
                    "Car is probably off, switch to slow polling: interval = %s",
                    self.update_interval,
                )
            else:
                self.update_interval = timedelta(seconds=self._fast_poll_interval)
                _LOGGER.debug(
                    "Car is on, polling: interval = %s",
                    self.update_interval,
                )
        except TimeoutError as err:
            raise UpdateFailed(f"BLE fetch timed out after {self._fetch_timeout}s") from err
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err
        else:
            if self.options.get("cache_values", False):
                self._cache_data.update(new_data)
                return self._cache_data
            return new_data

    @property
    def options(self) -> Mapping[str, Any]:
        """User configuration options."""
        return self._options

    @options.setter
    def options(self, options: Mapping[str, Any]) -> None:
        """Set the configuration options."""
        self._options = options
        self._fast_poll_interval: int = options.get("fast_poll", DEFAULT_FAST_POLL)
        self._slow_poll_interval: int = options.get("slow_poll", DEFAULT_SLOW_POLL)
        self._xs_poll_interval: int = options.get("xs_poll", DEFAULT_XS_POLL)
        self._cache_values: bool = options.get("cache_values", DEFAULT_CACHE_VALUES)
        self._fetch_timeout = float(options.get("fetch_timeout", DEFAULT_FETCH_TIMEOUT))


type NissanLeafObdBleConfigEntry = ConfigEntry[NissanLeafObdBleDataUpdateCoordinator]
