"""Config flow for the MDT RWIS integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import CannotConnect, InvalidAuth, async_get_sites
from .const import (
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    NAME,
)
from .coordinator import update_interval_minutes

_LOGGER = logging.getLogger(__name__)

KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class MdtRwisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add one RWIS site per config entry."""

    VERSION = 1

    def __init__(self) -> None:
        """Set up flow state."""
        self._api_key: str | None = None
        self._sites: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MdtRwisOptionsFlow:
        """Return the options flow."""
        return MdtRwisOptionsFlow()

    async def _validate_key(self, api_key: str) -> tuple[dict[str, str], str | None]:
        """Return (sites, error_key)."""
        try:
            sites = await async_get_sites(async_get_clientsession(self.hass), api_key)
        except InvalidAuth:
            return {}, "invalid_auth"
        except CannotConnect as err:
            _LOGGER.debug("Key check failed: %s", err)
            return {}, "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error checking the MDT API key")
            return {}, "unknown"
        if not sites:
            return {}, "no_sites"
        return sites, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the API key, prefilled from an existing entry if there is one."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            self._sites, error = await self._validate_key(api_key)
            if error is None:
                self._api_key = api_key
                return await self.async_step_site()
            errors["base"] = error

        suggested = user_input
        if suggested is None:
            existing = self._async_current_entries(include_ignore=False)
            if existing:
                suggested = {CONF_API_KEY: existing[0].data.get(CONF_API_KEY, "")}

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(KEY_SCHEMA, suggested),
            errors=errors,
        )

    async def async_step_site(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the site for this entry."""
        if user_input is not None:
            site_id = str(user_input[CONF_SITE_ID])
            await self.async_set_unique_id(f"{DOMAIN}_{site_id}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{NAME} - {self._sites.get(site_id, site_id)}",
                data={CONF_API_KEY: self._api_key, CONF_SITE_ID: site_id},
                options={CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
            )

        configured = {
            entry.data.get(CONF_SITE_ID) for entry in self._async_current_entries()
        }
        options = [
            SelectOptionDict(value=site_id, label=name)
            for site_id, name in sorted(
                self._sites.items(), key=lambda item: item[1].casefold()
            )
            if site_id not in configured
        ]
        if not options:
            return self.async_abort(reason="no_unconfigured_sites")

        return self.async_show_form(
            step_id="site",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=False,
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth after MDT rejects the stored key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new key and apply it to every entry that used the old one."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            _, error = await self._validate_key(api_key)
            if error is None:
                old_key = reauth_entry.data.get(CONF_API_KEY)
                for entry in self._async_current_entries():
                    if (
                        entry.entry_id != reauth_entry.entry_id
                        and entry.data.get(CONF_API_KEY) == old_key
                    ):
                        self.hass.config_entries.async_update_entry(
                            entry, data={**entry.data, CONF_API_KEY: api_key}
                        )
                        self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates={CONF_API_KEY: api_key}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=KEY_SCHEMA,
            description_placeholders={"site": reauth_entry.title},
            errors=errors,
        )


class MdtRwisOptionsFlow(OptionsFlowWithReload):
    """Change the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the interval form."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL])}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=update_interval_minutes(self.config_entry),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=MAX_UPDATE_INTERVAL,
                            step=1,
                            unit_of_measurement="min",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
