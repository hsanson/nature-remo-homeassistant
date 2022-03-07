""" Nature Remo Module """
import logging
from datetime import timedelta
from homeassistant import config_entries, core
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import (CONF_DEVICES, CONF_ENTITIES)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """ Setup platform from a ConfigEntry """

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )

    return True


class NatureRemoApi():
    """ Nature Remo API """

    def __init__(self, url: str, token: str, session):
        self.url = url
        self.token = token
        self.session = session

    async def get_me(self):
        """ Retrieve account details """
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/users/me", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json

    async def get_devices(self):
        """ Retrive list of devices """
        _LOGGER.debug("Fetching device list")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/devices", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json

    async def get_appliances(self):
        """ Retrive list of devices for a single device """
        _LOGGER.debug("Fetching appliances list")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/appliances", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json

    async def post(self, path, data):
        """Post any request"""
        _LOGGER.debug("Post:%s, data:%s", path, data)
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.post(
            f"{self.url}{path}", data=data, headers=headers
        )
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json


class NatureRemoApiError(Exception):
    """ Nature Remo API error exception """


class NatureRemoApiCoordinator(DataUpdateCoordinator):
    """ Nature Remo API Coordinator """

    def __init__(self, hass, api):
        super().__init__(
            hass,
            _LOGGER,
            name="Nature Remo",
            update_interval=timedelta(seconds=120),
        )
        self.api = api

    async def async_validate_token(self):
        """ Return account details """
        return await self.api.get_me()

    async def async_get_devices(self):
        """ Return dictionary of devices """
        return {x["id"]: x for x in await self.api.get_devices()}

    async def async_get_appliances(self):
        """ Return dictionary of appliances """
        return {x["id"]: x for x in await self.api.get_appliances()}

    async def async_post(self, path, data):
        """ Post data to Nature Remo cloud """
        return await self.api.post(path, data)

    async def _async_update_data(self):
        """ Fetch Nature Remo data from Cloud """
        _LOGGER.info("Fetching Nature Remo data")
        try:
            return {
                CONF_DEVICES: await self.async_get_devices(),
                CONF_ENTITIES: await self.async_get_appliances()
            }
        except NatureRemoApiError as error:
            raise UpdateFailed(f"Error communicating with Nature Remo API: {error}") from error
