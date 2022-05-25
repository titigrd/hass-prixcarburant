"""Prix Carburant sensor platform."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_NAME, CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_ADDRESS,
    ATTR_CITY,
    ATTR_FUELS,
    ATTR_POSTAL_CODE,
    ATTR_PRICE,
    CARBURANTS,
    CONF_MAX_KM,
    CONF_STATIONS,
    DOMAIN,
)
from .tools import PrixCarburantTool

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_MAX_KM): cv.positive_int,
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
    max_distance = options.get(CONF_MAX_KM, config.get(CONF_MAX_KM))

    tool = await hass.async_add_executor_job(PrixCarburantTool)

    async def async_update_data():
        """Fetch data from API."""
        await hass.async_add_executor_job(tool.update)
        return tool.stations

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=120),
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    if max_distance is not None:
        _LOGGER.info("Get stations near Home-Assistant location")
        config_stations_ids = tool.get_near_stations(
            hass.config.latitude,
            hass.config.longitude,
            max_distance,
            units=hass.config.units,
        )
    else:
        _LOGGER.info("Get stations from list in configuration")
        config_stations_ids = [str(s) for s in config.get(CONF_STATIONS, [])]

    user_stations_ids = [s for s in tool.stations if s in config_stations_ids]
    _LOGGER.info("%s stations found", str(len(user_stations_ids)))
    entities = []
    for station_id in user_stations_ids:
        for carburant in CARBURANTS:
            if carburant in tool.stations[station_id][ATTR_FUELS]:
                entities.append(
                    PrixCarburant(
                        station_id, tool.stations[station_id], carburant, coordinator
                    )
                )

    async_add_entities(entities, True)


class PrixCarburant(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, station_id, station_info, carburant, coordinator):
        """Initialize the sensor."""
        self.station_id = station_id
        self.station_info = station_info
        self.carburant = carburant
        self.coordinator = coordinator

        self._last_update = None

        self._attr_icon = "mdi:gas-station"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_unique_id = "_".join([DOMAIN, self.station_id, self.carburant])
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        if self.station_info[ATTR_NAME] != "undefined":
            station_name = f"Station {self.station_info[ATTR_NAME]}"
        else:
            station_name = f"Station {self.station_id}"
        self._attr_name = f"{station_name} {self.carburant}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
            manufacturer="Station",
            model=self.station_id,
            name=station_name,
            configuration_url="https://www.prix-carburants.gouv.fr/",
        )
        self._attr_extra_state_attributes = {
            ATTR_NAME: self.station_info[ATTR_NAME],
            ATTR_ADDRESS: self.station_info[ATTR_ADDRESS],
            ATTR_POSTAL_CODE: self.station_info[ATTR_POSTAL_CODE],
            ATTR_CITY: self.station_info[ATTR_CITY],
        }

    @property
    def native_value(self):
        """Return the current price."""
        if self.carburant in self.coordinator.data[self.station_id][ATTR_FUELS]:
            return self.coordinator.data[self.station_id][ATTR_FUELS][self.carburant][
                ATTR_PRICE
            ]
