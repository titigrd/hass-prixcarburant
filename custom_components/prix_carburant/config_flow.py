"""Config flow to configure the Prix Carburant integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import callback

from .const import CONF_FUELS, CONF_MAX_KM, CONF_STATIONS, DEFAULT_NAME, DOMAIN, FUELS


class PrixCarburantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Prix Carburant."""

    VERSION = 1

    async def async_step_import(self, import_info):
        """Import a config entry from YAML config."""
        entry = await self.async_set_unique_id(DOMAIN)

        if entry:
            self.hass.config_entries.async_update_entry(entry, data=import_info)
            self._abort_if_unique_id_configured()

        return self.async_create_entry(title=DEFAULT_NAME, data=import_info)

    async def async_step_user(self, user_input=None):
        """Get configuration from the user."""
        errors = {}
        if user_input is None:
            schema = {
                vol.Required(CONF_MAX_KM, default=10): int,
            }
            for fuel in FUELS:
                schema.update(
                    {
                        vol.Required(
                            f"{CONF_FUELS}_{fuel}",
                            default=True,
                        ): bool
                    }
                )
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(schema), errors=errors
            )

        entry = await self.async_set_unique_id(DOMAIN)

        if entry:
            self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=DEFAULT_NAME,
            data=user_input,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return PrixCarburantOptionsFlowHandler(config_entry)


class PrixCarburantOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a PrixCarburant options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input):
        """Manage the options."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=DEFAULT_NAME,
                data=user_input,
            )

        config = self.config_entry.data
        options = self.config_entry.options

        max_km = options.get(CONF_MAX_KM, config.get(CONF_MAX_KM))
        filtered_fuels = options.get(CONF_FUELS, config.get(CONF_FUELS, {}))

        schema = {}
        if CONF_STATIONS not in config:
            schema.update({vol.Required(CONF_MAX_KM, default=max_km): int})
        for fuel in FUELS:
            schema.update(
                {
                    vol.Required(
                        f"{CONF_FUELS}_{fuel}",
                        default=filtered_fuels.get(fuel, True),
                    ): bool
                }
            )

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )
