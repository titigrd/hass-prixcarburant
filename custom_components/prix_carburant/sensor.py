"""Prix Carburant sensor platform."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_NAME, CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA_BASE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_CITY,
    ATTR_DAYS_SINCE_LAST_UPDATE,
    ATTR_FUELS,
    ATTR_POSTAL_CODE,
    ATTR_PRICE,
    ATTR_UPDATED_DATE,
    CONF_FUELS,
    CONF_MAX_KM,
    CONF_STATIONS,
    DOMAIN,
    FUELS,
)
from .tools import PrixCarburantTool

_LOGGER = logging.getLogger(__name__)

# Validation of the yaml configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA_BASE.extend(
    {
        vol.Optional(CONF_STATIONS, default=[]): cv.ensure_list,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Prix Carburant sensor."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from config_entry."""
    config = entry.data
    options = entry.options

    websession = async_get_clientsession(hass)

    tool = PrixCarburantTool(time_zone=hass.config.time_zone, session=websession)

    # yaml configuration
    if CONF_STATIONS in config:
        _LOGGER.info("Init stations data from yaml list")
        await tool.init_stations_from_list(config[CONF_STATIONS])
    # ui configuration
    else:
        _LOGGER.info("Init stations list near Home-Assistant location")
        max_distance = options.get(CONF_MAX_KM, config.get(CONF_MAX_KM))
        await tool.init_stations_from_location(
            user_latitude=hass.config.latitude,
            user_longitude=hass.config.longitude,
            user_range=max_distance,
        )
        _LOGGER.info("%s stations found", str(len(tool.stations)))

    enabled_fuels = {}
    for fuel in FUELS:
        fuel_key = f"{CONF_FUELS}_{fuel}"
        enabled_fuels[fuel] = options.get(fuel_key, config.get(fuel_key, True))

    async def async_update_data():
        """Fetch data from API."""
        await tool.update_stations_prices()
        return tool.stations

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=60),
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    entities = []
    for station_id, station_data in tool.stations.items():
        for fuel in FUELS:
            if fuel in station_data[ATTR_FUELS] and enabled_fuels[fuel] is True:
                entities.append(
                    PrixCarburant(station_id, station_data, fuel, coordinator)
                )

    async_add_entities(entities, True)


class PrixCarburant(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, station_id, station_info, fuel, coordinator) -> None:
        """Initialize the sensor."""
        self.station_id = station_id
        self.station_info = station_info
        self.fuel = fuel
        self.coordinator = coordinator

        self._last_update = None

        self._attr_icon = "mdi:gas-station"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_unique_id = "_".join([DOMAIN, str(self.station_id), self.fuel])
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        if self.station_info[ATTR_NAME] != "undefined":
            station_name = f"Station {self.station_info[ATTR_NAME]}"
        else:
            station_name = f"Station {self.station_id}"
        self._attr_name = f"{station_name} {self.fuel}"

        match self.station_info[ATTR_BRAND]:
            case "Système U":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/fr/1/13/U_commer%C3%A7ants_logo_2018.svg"
            case "Total":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/fr/f/f7/Logo_TotalEnergies.svg"
            case "Total Access":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/fr/f/f7/Logo_TotalEnergies.svg"
            case "Intermarché":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/fr/8/8c/Logo_Groupe_Les_Mousquetaires.svg"
            case "Leclerc":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/commons/e/ed/Logo_E.Leclerc_Sans_le_texte.svg"
            case "Carrefour":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/commons/5/5b/Carrefour_logo.svg"
            case "Carrefour Market":
                self._attr_entity_picture = "https://upload.wikimedia.org/wikipedia/commons/4/4f/Carrefour_market_logo.svg"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
            manufacturer="Station",
            model=self.station_id,
            name=station_name,
            configuration_url="https://www.prix-carburants.gouv.fr/",
        )
        self._attr_extra_state_attributes = {
            ATTR_NAME: self.station_info[ATTR_NAME],
            ATTR_BRAND: self.station_info[ATTR_BRAND],
            ATTR_ADDRESS: self.station_info[ATTR_ADDRESS],
            ATTR_POSTAL_CODE: self.station_info[ATTR_POSTAL_CODE],
            ATTR_CITY: self.station_info[ATTR_CITY],
            ATTR_LATITUDE: self.station_info[ATTR_LATITUDE],
            ATTR_LONGITUDE: self.station_info[ATTR_LONGITUDE],
            ATTR_UPDATED_DATE: None,
            ATTR_DAYS_SINCE_LAST_UPDATE: None,
        }

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        fuel = self.coordinator.data[self.station_id][ATTR_FUELS].get(self.fuel)
        if fuel:
            # Update date in attributes
            self._attr_extra_state_attributes[ATTR_UPDATED_DATE] = fuel[
                ATTR_UPDATED_DATE
            ]
            try:
                delay = datetime.now() - datetime.strptime(
                    fuel[ATTR_UPDATED_DATE], "%Y-%m-%d %H:%M:%S"
                )
                self._attr_extra_state_attributes[
                    ATTR_DAYS_SINCE_LAST_UPDATE
                ] = delay.days
            except ValueError:
                _LOGGER.warning("Cannot calculate days between last update")
            # return price
            return float(fuel[ATTR_PRICE])
        return None
