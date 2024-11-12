"""Config flow for MDT RWIS integration."""
from __future__ import annotations
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    NAME,
    CONF_API_KEY,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    API_ALL_SITES,
    API_HEADERS,
)

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MDT RWIS."""
    
    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self.api_key = None
        self.sites = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step to enter the API key."""
        errors = {}

        # Check if an entry with the API key already exists
        existing_entries = self.hass.config_entries.async_entries(DOMAIN)
        if existing_entries:
            # Use the existing API key
            self.api_key = existing_entries[0].data[CONF_API_KEY]
            return await self.async_step_site()

        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]
            try:
                # Validate API key by attempting to fetch all sites
                self.sites = await self._fetch_all_sites(self.api_key)
                return await self.async_step_site()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during API key validation: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
        )

    async def async_step_site(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle site selection step after API key validation."""
        errors = {}

        if not self.sites:
            # Attempt to fetch sites again if they weren't fetched previously
            try:
                self.sites = await self._fetch_all_sites(self.api_key)
            except CannotConnect:
                return self.async_abort(reason="cannot_connect")
            except InvalidAuth:
                return self.async_abort(reason="invalid_auth")

        if user_input is not None:
            site_id = user_input[CONF_SITE_ID]
            await self.async_set_unique_id(f"{DOMAIN}_{site_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{NAME} - {self.sites[site_id]}",
                data={
                    CONF_API_KEY: self.api_key,
                    CONF_SITE_ID: site_id,
                    CONF_UPDATE_INTERVAL: user_input.get(
                        CONF_UPDATE_INTERVAL,
                        DEFAULT_UPDATE_INTERVAL
                    ),
                }
            )

        return self.async_show_form(
            step_id="site",
            data_schema=vol.Schema({
                vol.Required(CONF_SITE_ID): vol.In(self.sites),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=60)
                ),
            }),
            errors=errors,
        )

    async def _fetch_all_sites(self, api_key: str) -> dict:
        """Fetch all available sites to provide options for user selection."""
        session = aiohttp.ClientSession()
        url = API_ALL_SITES.format(api_key=api_key)
        _LOGGER.debug("Fetching all sites with URL: %s", url)

        async with session.get(url, headers=API_HEADERS) as resp:
            if resp.status == 401:
                _LOGGER.error("Invalid authentication: %s", resp.status)
                raise InvalidAuth
            if resp.status != 200:
                _LOGGER.error("Failed to connect to site API: %s", resp.status)
                raise CannotConnect

            data = await resp.json()
            _LOGGER.debug("Sites data received: %s", data)
            return {
                str(site["properties"]["id"]): site["properties"]["name"]
                for site in data["features"]
            }

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate invalid authentication credentials."""
