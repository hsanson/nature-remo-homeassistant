""" Support for Nature Remo AC """
import logging

from typing import Any, Dict
from homeassistant.components.climate import ClimateEntity
from homeassistant import config_entries, core
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES
)
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (TEMP_CELSIUS, ATTR_TEMPERATURE)
from . import (NatureRemoApi, NatureRemoApiCoordinator)
from .const import (BASE_URL, DOMAIN)

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_SWING_MODE

MODE_HA_TO_REMO = {
    HVAC_MODE_AUTO: "auto",
    HVAC_MODE_FAN_ONLY: "blow",
    HVAC_MODE_COOL: "cool",
    HVAC_MODE_DRY: "dry",
    HVAC_MODE_HEAT: "warm",
    HVAC_MODE_OFF: "power-off",
}

MODE_REMO_TO_HA = {
    "auto": HVAC_MODE_AUTO,
    "blow": HVAC_MODE_FAN_ONLY,
    "cool": HVAC_MODE_COOL,
    "dry": HVAC_MODE_DRY,
    "warm": HVAC_MODE_HEAT,
    "power-off": HVAC_MODE_OFF,
}


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """ Setup entities from a config_flow entry """
    config = hass.data[DOMAIN][config_entry.entry_id]
    session = async_get_clientsession(hass)
    api = NatureRemoApi(BASE_URL, config[CONF_ACCESS_TOKEN], session)
    coordinator = NatureRemoApiCoordinator(hass, api)
    device_id = config[CONF_DEVICE_ID]
    device = config[CONF_DEVICES][device_id]
    entities = []

    if CONF_ENTITIES in config:
        for _, appliance in config[CONF_ENTITIES].items():

            _LOGGER.info(appliance)
            # Ignore any appliance that do not belong to the device entry we are
            # registering
            if appliance["device"]["id"] != device_id:
                continue

            if appliance["type"] == "AC":
                entities.append(NatureRemoAC(device, appliance, coordinator))

        async_add_entities(entities, update_before_add=True)


class NatureRemoAC(CoordinatorEntity, ClimateEntity):
    """ Implement Nature Remo E sensor """

    def __init__(self, device: Dict[str, Any], appliance: Dict[str, Any],
                 coordinator: NatureRemoApiCoordinator):
        super().__init__(coordinator)
        self._name = f"{device['name']} - {appliance['model']['name']}"
        self._appliance_id = appliance["id"]
        self._available = True
        self._default_temp = {
            HVAC_MODE_COOL: 20,
            HVAC_MODE_HEAT: 20,
        }
        self._modes = appliance["aircon"]["range"]["modes"]
        self._hvac_mode = None
        self._current_temperature = None
        self._target_temperature = None
        self._remo_mode = None
        self._fan_mode = None
        self._swing_mode = None
        self._last_target_temperature = {v: None for v in MODE_REMO_TO_HA}
        self._device_id = device["id"]
        self._device_name = appliance['model']['name']
        self._manufacturer = appliance["model"]["manufacturer"]
        self._serial_number = device["serial_number"]
        self._firmware_version = device["firmware_version"]
        self._update(appliance["settings"], device)

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._appliance_id

    @property
    def available(self) -> bool:
        return self._available

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._appliance_id)},
            "name": self._device_name,
            "manufacturer": "Nature Remo",
            "model": self._serial_number,
            "sw_version": self._firmware_version,
        }

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) == 0:
            return 0
        return min(temp_range)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) == 0:
            return 0
        return max(temp_range)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        _LOGGER.debug("Current target temperature: %s", self._target_temperature)
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) >= 2:
            # determine step from the gap of first and second temperature
            step = round(temp_range[1] - temp_range[0], 1)
            if step in [1.0, 0.5]:  # valid steps
                return step
        return 1

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        remo_modes = list(self._modes.keys())
        ha_modes = list(map(lambda mode: MODE_REMO_TO_HA[mode], remo_modes))
        ha_modes.append(HVAC_MODE_OFF)
        return ha_modes

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """List of available fan modes."""
        return self._modes[self._remo_mode]["vol"]

    @property
    def swing_mode(self):
        """Return the swing setting."""
        return self._swing_mode

    @property
    def swing_modes(self):
        """List of available swing modes."""
        return self._modes[self._remo_mode]["dir"]

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return {
            "previous_target_temperature": self._last_target_temperature,
        }

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return
        if target_temp.is_integer():
            # has to cast to whole number otherwise API will return an error
            target_temp = int(target_temp)
        _LOGGER.debug("Set temperature: %d", target_temp)
        await self._post({"temperature": f"{target_temp}"})

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("Set hvac mode: %s", hvac_mode)
        mode = MODE_HA_TO_REMO[hvac_mode]
        if mode == MODE_HA_TO_REMO[HVAC_MODE_OFF]:
            await self._post({"button": mode})
        else:
            data = {
                "operation_mode": mode,
                "temperature": self._default_temp[hvac_mode]
            }

            if self._last_target_temperature[mode]:
                data["temperature"] = self._last_target_temperature[mode]

            await self._post(data)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        _LOGGER.debug("Set fan mode: %s", fan_mode)
        await self._post({"air_volume": fan_mode})

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        _LOGGER.debug("Set swing mode: %s", swing_mode)
        await self._post({"air_direction": swing_mode})

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    def _update(self, ac_settings, device=None):
        # hold this to determin the ac mode while it's turned-off
        self._remo_mode = ac_settings["mode"]
        self._target_temperature = float(ac_settings["temp"])
        self._last_target_temperature[self._remo_mode] = ac_settings["temp"]
        self._target_temperature = None

        if ac_settings["button"] == MODE_HA_TO_REMO[HVAC_MODE_OFF]:
            self._hvac_mode = HVAC_MODE_OFF
        else:
            self._hvac_mode = MODE_REMO_TO_HA[self._remo_mode]

        self._fan_mode = ac_settings["vol"] or None
        self._swing_mode = ac_settings["dir"] or None

        if device is not None:
            self._current_temperature = float(device["newest_events"]["te"]["val"])

    async def _post(self, data):
        response = await self.coordinator.async_post(
            f"/appliances/{self._appliance_id}/aircon_settings", data
        )
        self._update(response)

    def _current_mode_temp_range(self):
        temp_range = self._modes[self._remo_mode]["temp"]
        return list(map(float, filter(None, temp_range)))

    @core.callback
    def _handle_coordinator_update(self) -> None:
        device = self.coordinator.data[CONF_DEVICES][self._device_id]
        appliance = self.coordinator.data[CONF_ENTITIES][self._appliance_id]
        self._update(appliance["settings"], device)
        self.async_write_ha_state()
