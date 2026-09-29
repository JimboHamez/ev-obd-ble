"""Sensor platform for Nissan Leaf OBD BLE."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass

from .entity import NissanLeafObdBleEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import NissanLeafObdBleConfigEntry

# All values come from a single coordinator refresh, so entities never talk to
# the dongle themselves and need no update throttling.
PARALLEL_UPDATES = 0

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "gear_position": SensorEntityDescription(
        key="gear_position",
        translation_key="gear_position",
        icon="mdi:car-shift-pattern",
        device_class=SensorDeviceClass.ENUM,
    ),
    "bat_12v_voltage": SensorEntityDescription(
        key="bat_12v_voltage",
        translation_key="bat_12v_voltage",
        icon="mdi:car-battery",
        native_unit_of_measurement="V",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "bat_12v_current": SensorEntityDescription(
        key="bat_12v_current",
        translation_key="bat_12v_current",
        icon="mdi:car-battery",
        native_unit_of_measurement="A",
        suggested_display_precision=2,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "quick_charges": SensorEntityDescription(
        key="quick_charges",
        translation_key="quick_charges",
        icon="mdi:ev-plug-chademo",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "l1_l2_charges": SensorEntityDescription(
        key="l1_l2_charges",
        translation_key="l1_l2_charges",
        icon="mdi:ev-plug-type2",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ambient_temp": SensorEntityDescription(
        key="ambient_temp",
        translation_key="ambient_temp",
        icon="mdi:thermometer",
        native_unit_of_measurement="°C",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "estimated_ac_power": SensorEntityDescription(
        key="estimated_ac_power",
        translation_key="estimated_ac_power",
        icon="mdi:air-conditioner",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "estimated_ptc_power": SensorEntityDescription(
        key="estimated_ptc_power",
        translation_key="estimated_ptc_power",
        icon="mdi:heating-coil",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "aux_power": SensorEntityDescription(
        key="aux_power",
        translation_key="aux_power",
        icon="mdi:generator-portable",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ac_power": SensorEntityDescription(
        key="ac_power",
        translation_key="ac_power",
        icon="mdi:air-conditioner",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "plug_state": SensorEntityDescription(
        key="plug_state",
        translation_key="plug_state",
        icon="mdi:ev-plug-type1",
        device_class=SensorDeviceClass.ENUM,
    ),
    "charge_mode": SensorEntityDescription(
        key="charge_mode",
        translation_key="charge_mode",
        icon="mdi:ev-station",
        device_class=SensorDeviceClass.ENUM,
    ),
    "rpm": SensorEntityDescription(
        key="rpm",
        translation_key="rpm",
        icon="mdi:gauge",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "obc_out_power": SensorEntityDescription(
        key="obc_out_power",
        translation_key="obc_out_power",
        icon="mdi:generator-mobile",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "motor_power": SensorEntityDescription(
        key="motor_power",
        translation_key="motor_power",
        icon="mdi:engine",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "speed": SensorEntityDescription(
        key="speed",
        translation_key="speed",
        icon="mdi:speedometer",
        native_unit_of_measurement="km/h",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "odometer": SensorEntityDescription(
        key="odometer",
        translation_key="odometer",
        # icon="mdi:speedometer",
        native_unit_of_measurement="km",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "tp_fr": SensorEntityDescription(
        key="tp_fr",
        translation_key="tp_fr",
        # icon="mdi:speedometer",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "tp_fl": SensorEntityDescription(
        key="tp_fl",
        translation_key="tp_fl",
        # icon="mdi:speedometer",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "tp_rr": SensorEntityDescription(
        key="tp_rr",
        translation_key="tp_rr",
        # icon="mdi:speedometer",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "tp_rl": SensorEntityDescription(
        key="tp_rl",
        translation_key="tp_rl",
        # icon="mdi:speedometer",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "range_remaining": SensorEntityDescription(
        key="range_remaining",
        translation_key="range_remaining",
        # icon="mdi:speedometer",
        native_unit_of_measurement="km",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "state_of_charge": SensorEntityDescription(
        key="state_of_charge",
        translation_key="state_of_charge",
        icon="mdi:ev-station",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_health": SensorEntityDescription(
        key="hv_battery_health",
        translation_key="hv_battery_health",
        icon="mdi:battery-heart",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        # device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_Ah": SensorEntityDescription(
        key="hv_battery_Ah",
        translation_key="hv_battery_ah",
        # icon="mdi:ev-station",
        native_unit_of_measurement="Ah",
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_current_1": SensorEntityDescription(
        key="hv_battery_current_1",
        translation_key="hv_battery_current_1",
        # icon="mdi:ev-station",
        native_unit_of_measurement="A",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_current_2": SensorEntityDescription(
        key="hv_battery_current_2",
        translation_key="hv_battery_current_2",
        # icon="mdi:ev-station",
        native_unit_of_measurement="A",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_voltage": SensorEntityDescription(
        key="hv_battery_voltage",
        translation_key="hv_battery_voltage",
        # icon="mdi:ev-station",
        native_unit_of_measurement="V",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NissanLeafObdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator = entry.runtime_data
    entities = [NissanLeafObdBleSensor(coordinator, entry, desc) for desc in SENSOR_TYPES.values()]
    entities.extend(
        NissanLeafObdBleSensor(coordinator, entry, desc) for desc in coordinator.extra_sensor_descriptions.values()
    )
    async_add_entities(entities)


class NissanLeafObdBleSensor(NissanLeafObdBleEntity, SensorEntity):
    """Sensor reading a single decoded value from the coordinator."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)
