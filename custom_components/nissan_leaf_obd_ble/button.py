"""Button platform for Nissan Leaf OBD BLE."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NissanLeafObdBleConfigEntry
from .entity import NissanLeafObdBleEntity

# The button only asks the coordinator to refresh, so it needs no throttling.
PARALLEL_UPDATES = 0

REFRESH_BUTTON = ButtonEntityDescription(
    key="refresh",
    translation_key="refresh",
    icon="mdi:refresh",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NissanLeafObdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up button platform."""
    async_add_entities(
        [NissanLeafObdBleRefreshButton(entry.runtime_data, entry, REFRESH_BUTTON)]
    )


class NissanLeafObdBleRefreshButton(NissanLeafObdBleEntity, ButtonEntity):
    """Button that triggers an immediate coordinator refresh."""

    entity_description: ButtonEntityDescription

    async def async_press(self) -> None:
        """Trigger an immediate update."""
        await self.coordinator.async_request_refresh()
