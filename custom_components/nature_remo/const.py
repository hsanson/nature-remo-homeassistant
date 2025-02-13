""" Nature Remo Module Constants """

from homeassistant.components.sensor import (SensorDeviceClass)
from homeassistant.const import (UnitOfTemperature, PERCENTAGE, ILLUMINANCE)

DOMAIN = "nature_remo"
BASE_URL = "https://api.nature.global/1"
COORDINATOR = "nature_remo_coordinator"

SENSOR_NAMES = {
    "hu": "Humidity",
    "il": "Illumination",
    "te": "Temperature",
    "mo": "Motion"
}

SENSOR_CLASSES = {
    "hu": SensorDeviceClass.HUMIDITY,
    "il": SensorDeviceClass.ILLUMINANCE,
    "te": SensorDeviceClass.TEMPERATURE
}

SENSOR_UNITS = {
    "hu": PERCENTAGE,
    "il": ILLUMINANCE,
    "te": UnitOfTemperature.CELSIUS
}
