""" Support for Nature Remo Sensors """
import logging
from datetime import (datetime, timezone, timedelta)
from typing import Any, Dict
from dateutil import parser
from homeassistant import config_entries, core
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import (CONF_ACCESS_TOKEN, CONF_DEVICE_ID, CONF_DEVICES)
from homeassistant.components.sensor import (SensorEntity, SensorStateClass)
from homeassistant.components.binary_sensor import (BinarySensorEntity, BinarySensorDeviceClass)
from . import (NatureRemoApi, NatureRemoApiCoordinator)
from .const import (DOMAIN, BASE_URL, SENSOR_NAMES, SENSOR_UNITS, SENSOR_CLASSES)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """ Setup sensors from a config_flow entry """
    config = hass.data[DOMAIN][config_entry.entry_id]
    session = async_get_clientsession(hass)
    api = NatureRemoApi(BASE_URL, config[CONF_ACCESS_TOKEN], session)
    coordinator = NatureRemoApiCoordinator(hass, api)
    device_id = config[CONF_DEVICE_ID]
    device = config[CONF_DEVICES][device_id]
    sensors = []

    for sensor in device["newest_events"]:
        # Motion sensor is a different type so skipped here.
        if sensor != 'mo':
            sensors.append(NatureSensor(device, sensor, coordinator))

    if "mo" in device["newest_events"]:
        sensors.append(NatureMotionSensor(device, "mo", coordinator))

    async_add_entities(sensors, update_before_add=True)


class NatureSensor(CoordinatorEntity, SensorEntity):
    """ Nature Sensor Class """

    def __init__(self, device: Dict[str, Any], sensor: str, coordinator: NatureRemoApiCoordinator):
        super().__init__(coordinator)
        self._id = f"{device['id']}-{sensor}"
        self._sensor = sensor
        self._name = f"{device['name']} {SENSOR_NAMES[sensor]} Sensor"
        self._attr_native_value = device["newest_events"][sensor]["val"]
        self._attr_native_unit_of_measurement = SENSOR_UNITS[sensor]
        self._attr_device_class = SENSOR_CLASSES[sensor]
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._available = True
        self._device_id = device['id']
        self._device_name = device['name']
        self._serial_number = device["serial_number"]
        self._firmware_version = device["firmware_version"]

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._id

    @property
    def available(self) -> bool:
        return self._available

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Nature Remo",
            "model": self._serial_number,
            "sw_version": self._firmware_version,
        }

    async def async_update(self):
        """ Update sensor """
        await self.coordinator.async_request_refresh()

    @core.callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.info("Updating Nature Remo sensors")
        device = self.coordinator.data[CONF_DEVICES][self._device_id]
        self._attr_native_value = device["newest_events"][self._sensor]["val"]
        self._available = True
        self.async_write_ha_state()


class NatureMotionSensor(CoordinatorEntity, BinarySensorEntity):
    """
    Nature Remo Motion Sensor
    The sensor value is always one. Whenever motion is detected the created_at
    field is updated. To determine motion we check if no updates happened in 1
    minute.
    """

    def __init__(self, device: Dict[str, Any], sensor: str, coordinator: NatureRemoApiCoordinator):
        super().__init__(coordinator)
        self._id = f"{device['id']}-{sensor}"
        self._sensor = sensor
        self._name = f"{device['name']} {SENSOR_NAMES[sensor]} Sensor"
        self._last_update = parser.parse(device["newest_events"][self._sensor]["created_at"])
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._available = True
        self._device_id = device['id']
        self._device_name = device['name']
        self._serial_number = device["serial_number"]
        self._firmware_version = device["firmware_version"]

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._id

    @property
    def available(self) -> bool:
        return self._available

    @property
    def is_on(self) -> bool:
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_update).seconds
        return elapsed < 60

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Nature Remo",
            "model": self._serial_number,
            "sw_version": self._firmware_version,
        }

    async def async_update(self):
        """ Update sensor"""
        await self.coordinator.async_request_refresh()

    @core.callback
    def _handle_coordinator_update(self) -> None:
        device = self.coordinator.data[CONF_DEVICES][self._device_id]
        self._last_update = parser.parse(device["newest_events"][self._sensor]["created_at"])
        self._available = True
        self.async_write_ha_state()
