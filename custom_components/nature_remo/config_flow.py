""" Nature Remo Config Flow Module """
import logging
from typing import Any, Dict, Optional
from homeassistant.const import (
    CONF_ACCESS_TOKEN, CONF_DEVICE_ID,
    CONF_DEVICES, CONF_ENTITIES
)
from homeassistant import config_entries, core
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from . import (NatureRemoApi, NatureRemoApiError, NatureRemoApiCoordinator)
from .const import (DOMAIN, BASE_URL)

_LOGGER = logging.getLogger(__name__)


class NatureRemoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ Nature Remo Config Flow """

    def __init__(self):
        self._token = ""
        self._discovered_devices = {}
        self._discovered_entities = {}
        self._coordinator = Any

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """ Invoked when a user initiates a flow via user interface """
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                _LOGGER.info("Check token validity")
                self._token = user_input[CONF_ACCESS_TOKEN]
                session = async_get_clientsession(self.hass)
                api = NatureRemoApi(BASE_URL, self._token, session)
                self._coordinator = NatureRemoApiCoordinator(self.hass, api)
                await self._coordinator.async_validate_token()
            except NatureRemoApiError as error:
                _LOGGER.error("Could not connect to Nature Remo cloud - %s", error)
                errors["base"] = "auth"

            if not errors:
                self.data = user_input
                return await self.async_step_pick_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ACCESS_TOKEN): cv.string}),
            errors=errors,
        )

    async def async_step_pick_device(self, user_input: Optional[Dict[str, Any]] = None):
        """ Pick device from list of discovered devices """
        errors: Dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            await self.async_set_unique_id(device_id, raise_on_progress=False)
            return self._async_create_entry_from_device(self._discovered_devices[device_id])

        configured_devices = {
            entry.unique_id for entry in self._async_current_entries()
        }

        try:
            self._discovered_devices = await self._discover_devices()
            self._discovered_entities = await self._discover_entities()
        except NatureRemoApiError as error:
            _LOGGER.error("Could not get list of devices/appliances - %s", error)
            return self.async_abort(reason="connection_fail")

        devices_name = {
            device_id: f"{device['name']} {device['serial_number']}"
            for device_id, device in self._discovered_devices.items()
            if device_id not in configured_devices
        }

        if not devices_name:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(devices_name)}),
            errors=errors,
        )

    async def _discover_devices(self):
        """ Discover devices from Nature Remo cloud account """
        return await self._coordinator.async_get_devices()

    async def _discover_entities(self):
        """ Discover entities (appliances) from Nature Remo cloud account """
        return await self._coordinator.async_get_appliances()

    @core.callback
    def _async_create_entry_from_device(self, device):
        """ Create config entry for Nature Remo device """
        self._abort_if_unique_id_configured(updates={CONF_DEVICE_ID: device["id"]})
        _LOGGER.info(self._discovered_entities)
        return self.async_create_entry(
            title=f"{device['name']} {device['serial_number']}",
            data={
                CONF_ACCESS_TOKEN: self._token,
                CONF_DEVICE_ID: device["id"],
                CONF_DEVICES: self._discovered_devices,
                CONF_ENTITIES: self._discovered_entities
            },
        )
