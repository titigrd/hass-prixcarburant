"""Prix Carburant integration."""
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_ADDRESS,
    ATTR_CITY,
    ATTR_POSTAL_CODE,
    ATTR_PRICE,
    CONF_MAX_KM,
    CONF_STATIONS,
    DOMAIN,
    PLATFORMS,
)
from .tools import PrixCarburantTool

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config = entry.data
    options = entry.options

    websession = async_get_clientsession(hass)

    tool = PrixCarburantTool(time_zone=hass.config.time_zone, session=websession)

    # yaml configuration
    if CONF_STATIONS in config:
        _LOGGER.info("Init stations data from yaml list")
        await tool.init_stations_from_list(
            stations_ids=config[CONF_STATIONS],
            latitude=hass.config.latitude,
            longitude=hass.config.longitude,
        )
    # ui configuration
    else:
        _LOGGER.info("Init stations list near Home-Assistant location")
        max_distance = options.get(CONF_MAX_KM, config.get(CONF_MAX_KM))
        await tool.init_stations_from_location(
            latitude=hass.config.latitude,
            longitude=hass.config.longitude,
            distance=max_distance,
        )
        _LOGGER.info("%s stations found", str(len(tool.stations)))

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

    hass.data[DOMAIN][entry.entry_id] = {"tool": tool, "coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def find_nearest_stations(call: ServiceCall) -> ServiceResponse:
        """Search in the date range and return the matching items."""
        fuel = call.data["fuel"]
        distance = call.data["distance"]
        entity_id = call.data["entity_id"]
        entity = hass.states.get(entity_id)
        if not entity:
            raise HomeAssistantError("The entity specified was not found")
        entity_longitude = entity.attributes.get("longitude")
        entity_latitude = entity.attributes.get("latitude")
        if not entity_longitude and not entity_latitude:
            raise HomeAssistantError(
                "The entity specified must have latitude and longitude attribute"
            )
        stations = await tool.find_nearest_station(
            entity_longitude, entity_latitude, fuel, distance
        )
        return {
            "stations": [
                {
                    "name": station_data[ATTR_NAME],
                    "price": station_data.get(ATTR_PRICE),
                    "address": f"{station_data[ATTR_ADDRESS]}, {station_data[ATTR_POSTAL_CODE]} {station_data[ATTR_CITY]}",
                }
                for station_id, station_data in stations.items()
            ],
        }

    hass.services.async_register(
        DOMAIN,
        "find_nearest_stations",
        find_nearest_stations,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
