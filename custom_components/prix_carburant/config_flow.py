"""Config flow to configure the Prix Carburant integration."""
from __future__ import annotations

from collections.abc import Mapping

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_FUELS, CONF_MAX_KM, DEFAULT_MAX_KM, DEFAULT_NAME, DOMAIN, FUELS


def _build_schema(config: Mapping, options: Mapping) -> vol.Schema:
    """Build schema according to config/options."""
    max_km = options.get(CONF_MAX_KM, config.get(CONF_MAX_KM, DEFAULT_MAX_KM))
    schema = {
        vol.Required(CONF_MAX_KM, default=max_km): int,
    }
    for fuel in FUELS:
        fuel_key = f"{CONF_FUELS}_{fuel}"
        schema.update(
            {
                vol.Required(
                    fuel_key,
                    default=options.get(fuel_key, config.get(fuel_key, True)),
                ): bool
            }
        )
    return vol.Schema(schema)


class PrixCarburantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Prix Carburant."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Get configuration from the user."""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=_build_schema({}, {}), errors=errors
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
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Define the config flow to handle options."""
        return PrixCarburantOptionsFlowHandler(config_entry)


class PrixCarburantOptionsFlowHandler(OptionsFlow):
    """Handle a PrixCarburant options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(
                title=DEFAULT_NAME,
                data=user_input,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                self.config_entry.data, self.config_entry.options
            ),
            errors=errors,
        )
