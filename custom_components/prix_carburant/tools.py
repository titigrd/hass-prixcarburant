"""Tools for Prix Carburant."""
from asyncio import timeout
import json
import logging
import os
from socket import gaierror

from aiohttp import ClientError, ClientSession

from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_NAME

from .const import (
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_CITY,
    ATTR_FUELS,
    ATTR_POSTAL_CODE,
    ATTR_PRICE,
    ATTR_UPDATED_DATE,
    FUELS,
)

_LOGGER = logging.getLogger(__name__)

PRIX_CARBURANT_API_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records"
STATIONS_NAME_FILE = "stations_name.json"


class PrixCarburantTool:
    """Prix Carburant class with stations information."""

    def __init__(
        self,
        user_latitude: float,
        user_longitude: float,
        user_range: int,
        time_zone: str = "Europe/Paris",
        request_timeout: int = 30,
        session: ClientSession | None = None,
    ) -> None:
        """Init tool."""
        self._user_latitude = user_latitude
        self._user_longitude = user_longitude
        self._user_range = user_range
        self._user_time_zone = time_zone
        self._stations_names: dict[str, dict] = {}
        self._stations_data: dict[str, dict] = {}

        self._request_timeout = request_timeout
        self._session = session
        self._close_session = False

        if self._session is None:
            self._session = ClientSession()
            self._close_session = True

    @property
    def stations(self) -> dict:
        """Return stations information."""
        return self._stations_data

    async def _request_api(
        self,
        params: dict,
    ) -> dict:
        """Make a request to the JSON API."""
        try:
            params.update(
                {
                    "lang": "fr",
                    "timezone": self._user_time_zone,
                }
            )
            async with timeout(self._request_timeout):
                response = await self._session.request(  # type: ignore[union-attr]
                    method="GET", url=PRIX_CARBURANT_API_URL, params=params
                )
                content = await response.json()

                if response.status == 200 and "results" in content:
                    response.close()
                    return content

                raise PrixCarburantToolRequestError(
                    f"API request error {response.status}: {content}"
                )

        except TimeoutError as exception:
            raise PrixCarburantToolCannotConnectError(
                "Timeout occurred while connecting to Prix Carburant API."
            ) from exception
        except (ClientError, gaierror) as exception:
            raise PrixCarburantToolCannotConnectError(
                "Error occurred while communicating with the Prix Carburant API."
            ) from exception

    async def init_stations_data(self) -> None:
        """Get data from all stations."""
        _LOGGER.debug("load stations names from: %s", STATIONS_NAME_FILE)
        with open(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), STATIONS_NAME_FILE
            ),
            encoding="UTF-8",
        ) as file:
            self._stations_names = json.load(file)

        data = {}
        _LOGGER.debug("call %s API for station data retrieval", PRIX_CARBURANT_API_URL)
        response_count = await self._request_api(
            {
                "select": "id",
                "where": f"distance(geom, geom'POINT({self._user_longitude} {self._user_latitude})', {self._user_range}km)",
                "limit": 1,
            }
        )
        stations_count = response_count["total_count"]
        _LOGGER.debug("%s stations returned by the API", stations_count)

        for query_offset in range(0, stations_count, 100):
            query_limit = (
                100
                if query_offset < stations_count - 100
                else stations_count - query_offset
            )
            _LOGGER.debug(
                "query stations from %s to %s/%s",
                query_offset,
                query_limit,
                stations_count,
            )
            async with timeout(self._request_timeout):
                response = await self._request_api(
                    {
                        "select": "id,latitude,longitude,cp,adresse,ville",
                        "where": f"distance(geom, geom'POINT({self._user_longitude} {self._user_latitude})', {self._user_range}km)",
                        "offset": query_offset,
                        "limit": query_limit,
                    }
                )
            for station in response["results"]:
                try:
                    data.update(
                        {
                            station["id"]: {
                                ATTR_LATITUDE: float(station["latitude"]) / 100000,
                                ATTR_LONGITUDE: float(station["longitude"]) / 100000,
                                ATTR_ADDRESS: station["adresse"],
                                ATTR_POSTAL_CODE: station["cp"],
                                ATTR_CITY: station["ville"],
                                ATTR_NAME: "undefined",
                                ATTR_BRAND: None,
                                ATTR_FUELS: {},
                            }
                        }
                    )
                    # add station name if existing in local data
                    if str(station["id"]) in self._stations_names:
                        data[station["id"]][ATTR_NAME] = (
                            str(self._stations_names[str(station["id"])]["Nom"])
                            .title()
                            .replace("Station ", "")
                        )
                        data[station["id"]][ATTR_BRAND] = str(
                            self._stations_names[str(station["id"])]["Marque"]
                        ).title()

                except (KeyError, TypeError) as error:
                    _LOGGER.error(
                        "Error while getting station %s information: %s",
                        station.get("id", "no ID"),
                        error,
                    )

        self._stations_data = data

    async def update_stations_prices(self) -> None:
        """Update tarifs of specified stations."""
        _LOGGER.debug("call %s API for station data retrieval", PRIX_CARBURANT_API_URL)
        for station_id, station_data in self._stations_data.items():
            _LOGGER.debug(
                "Update fuel prices for station id %s: %s",
                station_id,
                station_data[ATTR_NAME],
            )

            query_select = ",".join(
                [f"{f.lower()}_prix" for f in FUELS]
                + [f"{f.lower()}_maj" for f in FUELS]
            )

            response = await self._request_api(
                {
                    "select": query_select,
                    "where": f"id={station_id}",
                    "limit": 1,
                }
            )
            if response["total_count"] != 1:
                _LOGGER.error(
                    "%s stations returned, must be 1", response["total_count"]
                )
                continue
            new_prices = response["results"][0]
            for fuel in FUELS:
                fuel_key = fuel.lower()
                if new_prices[f"{fuel_key}_prix"]:
                    station_data[ATTR_FUELS].update(
                        {
                            fuel: {
                                ATTR_UPDATED_DATE: new_prices[f"{fuel_key}_maj"],
                                ATTR_PRICE: new_prices[f"{fuel_key}_prix"],
                            }
                        }
                    )


class PrixCarburantToolCannotConnectError(Exception):
    """Exception to indicate an error in connection."""


class PrixCarburantToolRequestError(Exception):
    """Exception to indicate an error with an API request."""
