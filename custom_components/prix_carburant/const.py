"""Constants for the Prix Carburant integration."""
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "prix_carburant"
PLATFORMS: Final = [Platform.SENSOR]

DEFAULT_NAME: Final = "Prix Carburant"

ATTR_ADDRESS = "address"
ATTR_POSTAL_CODE = "postal_code"
ATTR_CITY = "city"
ATTR_FUELS = "fuels"
ATTR_PRICE = "price"
CONF_STATIONS = "stations"
CONF_MAX_KM = "max_km"

ATTR_GAZOLE = "Gazole"
ATTR_SP95 = "SP95"
ATTR_SP98 = "SP98"
ATTR_E10 = "E10"
ATTR_E85 = "E85"
ATTR_GPL = "GPLc"
CARBURANTS = [ATTR_E10, ATTR_E85, ATTR_SP95, ATTR_SP98, ATTR_GAZOLE, ATTR_GPL]
