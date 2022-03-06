""" Nature Remo Module """
import logging
from homeassistant import config_entries, core

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

    async def get_device(self, device_id: str):
        """ Retrieve single device """
        _LOGGER.debug("Fetching device %s", device_id)
        devices = {x["id"]: x for x in await self.get_devices()}
        if device_id in devices:
            return devices[device_id]

        raise NatureRemoApiError("Connection error: 404001 device not found")

    async def get_devices(self):
        """ Retrive list of devices """
        _LOGGER.debug("Fetching device list")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/devices", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json

    async def get_appliance(self, appliance_id: str):
        """ Retrieve single appliance """
        _LOGGER.debug("Fetching appliance %s", appliance_id)
        appliances = {x["id"]: x for x in await self.get_appliances()}
        if appliance_id in appliances:
            return appliances[appliance_id]

        raise NatureRemoApiError("Connection error: 404001 device not found")

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
