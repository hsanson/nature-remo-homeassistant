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

    return True


class NatureRemoApi():
    """ Nature Remo API """

    def __init__(self, url: str, token: str, session):
        self.url = url
        self.token = token
        self.session = session

    async def get_me(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/users/me", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json

    async def get_device(self, device_id: str):
        _LOGGER.debug("Fetching device %s", device_id)
        devices = {x["id"]: x for x in await self.get_devices()}
        if device_id in devices:
            return devices[device_id]

        raise NatureRemoApiError("Connection error: 404001 device not found")

    async def get_devices(self):
        _LOGGER.debug("Fetching device list")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/devices", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return json

    async def get_appliances(self):
        _LOGGER.debug("Fetching appliances list")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.session.get(f"{self.url}/appliances", headers=headers)
        json = await response.json()
        if "code" in json:
            raise NatureRemoApiError(f"Connection error: {json['code']} {json['message']}")
        return await json


class NatureRemoApiError(Exception):
    pass
