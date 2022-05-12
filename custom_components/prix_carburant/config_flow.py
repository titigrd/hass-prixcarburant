"""Config flow to configure the Prix Carburant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DEFAULT_NAME, DOMAIN


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
        return self.async_abort(reason="yaml_only")
