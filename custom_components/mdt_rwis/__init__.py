"""The MDT RWIS integration."""
from __future__ import annotations
from datetime import timedelta
import logging

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    API_SITE_DATA,  # Replaced API_CURRENT_CONDITIONS
    API_SITE_IMAGES,  # Corrected to API_SITE_IMAGES
    API_HEADERS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.CAMERA,  
]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MDT RWIS component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MDT RWIS from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    site_id = entry.data[CONF_SITE_ID]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    session = async_get_clientsession(hass)

    async def async_update_data():
        """Fetch data from API for the selected site."""
        try:
            async with async_timeout.timeout(10):
                # Use formatted URLs with dynamic substitution
                weather_url = API_SITE_DATA.format(site_id=site_id, api_key=api_key)
                camera_url = API_SITE_IMAGES.format(site_id=site_id, api_key=api_key)
                
                # Fetch weather data
                _LOGGER.debug("Fetching weather data from %s", weather_url)
                async with session.get(weather_url, headers=API_HEADERS) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("Weather data fetch failed: %s - %s", resp.status, text)
                        raise UpdateFailed(f"Error fetching weather data: {resp.status}")
                    
                    weather_data = await resp.json()
                    _LOGGER.debug("Weather data received: %s", weather_data)

                # Fetch camera data
                _LOGGER.debug("Fetching camera data from %s", camera_url)
                async with session.get(camera_url, headers=API_HEADERS) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("Camera data fetch failed: %s - %s", resp.status, text)
                        raise UpdateFailed(f"Error fetching camera data: {resp.status}")
                    
                    camera_data = await resp.json()
                    _LOGGER.debug("Camera data received: %s", camera_data)

                return {
                    "weather": weather_data,
                    "cameras": camera_data,
                }
        except Exception as err:
            _LOGGER.error("Error fetching data: %s", err)
            raise UpdateFailed(f"Error fetching data: {err}")



    # Coordinator setup for fetching data periodically
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=update_interval),
    )

    # Store coordinator and configuration data for access by platforms
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_key": api_key,
        "site_id": site_id,
    }

    # Perform the initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Forward entry setups for specified platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
