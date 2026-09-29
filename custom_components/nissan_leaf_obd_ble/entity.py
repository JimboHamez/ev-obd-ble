"""Base entity for Nissan Leaf OBD BLE."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import NissanLeafObdBleConfigEntry, NissanLeafObdBleDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class NissanLeafObdBleEntity(CoordinatorEntity[NissanLeafObdBleDataUpdateCoordinator]):
    """Base class for entities backed by the OBD BLE coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NissanLeafObdBleDataUpdateCoordinator,
        config_entry: NissanLeafObdBleConfigEntry,
        description: EntityDescription,
    ) -> None:
        """Initialise the entity against its coordinator and description."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.entity_description = description

        address: str = config_entry.data[CONF_ADDRESS]
        self._attr_unique_id = f"{address}-{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=NAME,
            manufacturer=NAME,
            model=VERSION,
        )
