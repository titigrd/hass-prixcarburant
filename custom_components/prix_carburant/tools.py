"""Tools for Prix Carburant."""
import csv
from datetime import datetime
import logging
from math import asin, cos, radians, sin, sqrt
import urllib.request
import zipfile

import xmltodict

from homeassistant.const import ATTR_DATE, ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_NAME
from homeassistant.util.unit_system import METRIC_SYSTEM, UnitSystem

from .const import (
    ATTR_ADDRESS,
    ATTR_CITY,
    ATTR_FUELS,
    ATTR_POSTAL_CODE,
    ATTR_PRICE,
    ATTR_UPDATED_DATE,
)

_LOGGER = logging.getLogger(__name__)

STATIONS_DATA_URL = "https://static.data.gouv.fr/resources/prix-des-carburants-en-france/20181117-111538/active-stations.csv"
STATIONS_TARIFS_URL = "https://donnees.roulez-eco.fr/opendata/instantane"


class PrixCarburantTool:
    """Prix Carburant class with stations information."""

    def __init__(self):
        """Init tool."""
        self._stations_names = {}
        self._stations_tarifs = {}

        self._get_stations_names()

    @property
    def stations(self) -> dict:
        """Return stations information."""
        return self._stations_tarifs

    def update(self) -> None:
        """Update tarifs."""
        if not self._stations_names:
            raise Exception("call load() first")
        self._get_stations_tarifs()
        # add station name
        for station in self._stations_tarifs.items():
            station_id = station[0]
            if station_id in self._stations_names:
                self._stations_tarifs[station_id][ATTR_NAME] = (
                    str(self._stations_names[station_id])
                    .title()
                    .replace("Station ", "")
                )

    def _get_stations_names(self) -> None:
        filehandle, _ = urllib.request.urlretrieve(STATIONS_DATA_URL)
        data = {}
        with open(filehandle, newline="", encoding="UTF-8") as file:
            spamreader = csv.reader(file, delimiter=",", quotechar='"')
            for row in spamreader:
                data.update({row[0]: row[1]})
        self._stations_names = data

    def _get_stations_tarifs(self) -> None:
        """Update data from all stations."""
        data = {}
        filehandle, _ = urllib.request.urlretrieve(STATIONS_TARIFS_URL)
        with zipfile.ZipFile(filehandle, "r") as zip_file_object:
            with zip_file_object.open(zip_file_object.namelist()[0]) as file:
                file_date = datetime(*zip_file_object.NameToInfo[file.name].date_time)
                xml_content = file.read()
                raw_content = xmltodict.parse(xml_content)
                for station in raw_content["pdv_liste"]["pdv"]:
                    try:
                        data.update(
                            {
                                station["@id"]: {
                                    ATTR_LATITUDE: float(station["@latitude"]) / 100000,
                                    ATTR_LONGITUDE: float(station["@longitude"])
                                    / 100000,
                                    ATTR_ADDRESS: station["adresse"],
                                    ATTR_POSTAL_CODE: station["@cp"],
                                    ATTR_CITY: station["ville"],
                                    ATTR_NAME: "undefined",
                                    ATTR_UPDATED_DATE: file_date,
                                    ATTR_FUELS: {},
                                }
                            }
                        )
                        if "prix" in station:
                            for fuel in station["prix"]:
                                fuel_info = (
                                    fuel if isinstance(fuel, dict) else station["prix"]
                                )
                                data[station["@id"]][ATTR_FUELS].update(
                                    {
                                        fuel_info["@nom"]: {
                                            ATTR_DATE: fuel_info["@maj"],
                                            ATTR_PRICE: fuel_info["@valeur"],
                                        }
                                    }
                                )
                    except (KeyError, TypeError) as error:
                        _LOGGER.error(
                            "Error while getting station %s information: %s",
                            station["@id"],
                            error,
                        )

        self._stations_tarifs = data

    def get_near_stations(
        self,
        latitude: float,
        longitude: float,
        distance: int,
        units: UnitSystem = METRIC_SYSTEM,
    ) -> list:
        """Return list of station near the location."""
        near_stations_ids = []
        for station_id, station_info in self._stations_tarifs.items():
            if station_info[ATTR_LATITUDE] and station_info[ATTR_LONGITUDE]:
                station_distance = _get_distance(
                    latitude,
                    longitude,
                    float(station_info[ATTR_LATITUDE]),
                    float(station_info[ATTR_LONGITUDE]),
                    units,
                )
                if station_distance <= distance:
                    near_stations_ids.append(station_id)
        return near_stations_ids


def _get_distance(
    lon1: float, lat1: float, lon2: float, lat2: float, units: UnitSystem
) -> int:
    """Get distance from 2 locations."""
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    angle = 2 * asin(
        sqrt(sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2)
    )
    earth_radius = 6371 if units == METRIC_SYSTEM else 3956
    return int(angle * earth_radius)
