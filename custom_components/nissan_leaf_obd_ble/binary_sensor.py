"""Binary sensor platform for Nissan Leaf OBD BLE."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

from .entity import NissanLeafObdBleEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import NissanLeafObdBleConfigEntry

# All values come from a single coordinator refresh, so entities never talk to
# the dongle themselves and need no update throttling.
PARALLEL_UPDATES = 0

BINARY_SENSOR_TYPES: dict[str, BinarySensorEntityDescription] = {
    "power_switch": BinarySensorEntityDescription(
        key="power_switch",
        translation_key="power_switch",
        icon="mdi:power",
    ),
    "ac_on": BinarySensorEntityDescription(
        key="ac_on",
        translation_key="ac_on",
        icon="mdi:air-conditioner",
    ),
    "rear_heater": BinarySensorEntityDescription(
        key="rear_heater",
        translation_key="rear_heater",
        icon="mdi:heat-wave",
    ),
    "eco_mode": BinarySensorEntityDescription(
        key="eco_mode",
        translation_key="eco_mode",
        icon="mdi:sprout",
    ),
    "e_pedal_mode": BinarySensorEntityDescription(
        key="e_pedal_mode",
        translation_key="e_pedal_mode",
        icon="mdi:bike-pedal",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NissanLeafObdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary_sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(NissanLeafObdBleBinarySensor(coordinator, entry, desc) for desc in BINARY_SENSOR_TYPES.values())


class NissanLeafObdBleBinarySensor(NissanLeafObdBleEntity, BinarySensorEntity):
    """Binary sensor reading a single decoded flag from the coordinator."""

    entity_description: BinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.get(self.entity_description.key)
