"""Diagnostics for the MDT RWIS integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import MdtRwisConfigEntry

# apiKey covers any echo of the key inside the payload.
TO_REDACT = {CONF_API_KEY, "apiKey"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MdtRwisConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "payload": async_redact_data(
            {"weather": data.weather, "images": data.images} if data else {},
            TO_REDACT,
        ),
    }
