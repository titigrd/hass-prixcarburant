"""Config flow to configure the Prix Carburant integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import callback

from .const import CONF_MAX_KM, CONF_STATIONS, DEFAULT_NAME, DOMAIN


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
            schema = vol.Schema({vol.Required(CONF_MAX_KM, default=10): int})
            return self.async_show_form(
                step_id="user", data_schema=schema, errors=errors
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

        if CONF_STATIONS in config:
            return self.async_abort(reason="yaml_configuration")

        max_km = options.get(CONF_MAX_KM, config.get(CONF_MAX_KM))

        schema = vol.Schema({vol.Required(CONF_MAX_KM, default=max_km): int})

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
