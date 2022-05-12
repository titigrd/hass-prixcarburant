"""Tools for Prix Carburant."""
import csv
import logging
import urllib.request
import zipfile

import xmltodict

from homeassistant.const import ATTR_DATE, ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_NAME

from .const import ATTR_ADDRESS, ATTR_CITY, ATTR_FUELS, ATTR_POSTAL_CODE, ATTR_PRICE

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
                xml_content = file.read()
                raw_content = xmltodict.parse(xml_content)
                for station in raw_content["pdv_liste"]["pdv"]:
                    try:
                        data.update(
                            {
                                station["@id"]: {
                                    ATTR_LATITUDE: station["@latitude"],
                                    ATTR_LONGITUDE: station["@longitude"],
                                    ATTR_ADDRESS: station["adresse"],
                                    ATTR_POSTAL_CODE: station["@cp"],
                                    ATTR_CITY: station["ville"],
                                    ATTR_NAME: "undefined",
                                    ATTR_FUELS: {},
                                }
                            }
                        )
                        if "prix" in station:
                            for carburant in station["prix"]:
                                carburant_info = (
                                    carburant
                                    if isinstance(carburant, dict)
                                    else station["prix"]
                                )
                                data[station["@id"]][ATTR_FUELS].update(
                                    {
                                        carburant_info["@nom"]: {
                                            ATTR_DATE: carburant_info["@maj"],
                                            ATTR_PRICE: carburant_info["@valeur"],
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
