"""Camera platform for MDT RWIS integration."""
from __future__ import annotations
import logging
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MDT RWIS cameras."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    cameras = []
    if coordinator.data:
        station_data = coordinator.data["cameras"]["features"][0]["properties"]
        if "cameras" in station_data:
            station_name = coordinator.data["weather"]["features"][0]["properties"]["name"]
            for camera in station_data["cameras"]:
                cameras.append(RWISCamera(
                    coordinator,
                    station_data["id"],
                    camera,
                    station_name,
                    hass
                ))

    async_add_entities(cameras)

class RWISCamera(CoordinatorEntity, Camera):
    """MDT RWIS camera entity - static JPEG only."""

    def __init__(self, coordinator, site_id, camera_data, station_name, hass):
        """Initialize the camera."""
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        
        self.site_id = site_id
        self._camera_id = camera_data["id"]
        self._camera_data = camera_data
        self.hass = hass
        
        self._attr_name = camera_data["name"]
        self._attr_unique_id = f"rwis_camera_{self._camera_id}"
        
        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, site_id)},
            "name": station_name,
            "manufacturer": "Montana DOT",
            "model": "RWIS Camera",
        }

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return bytes of camera image."""
        try:
            camera_data = self._get_camera_data()
            if not camera_data:
                _LOGGER.error("No camera data available")
                return None

            session = async_get_clientsession(self.hass)
            async with session.get(camera_data["image"]) as resp:
                if resp.status == 200:
                    return await resp.read()
                _LOGGER.error("Failed to fetch image, status code: %s", resp.status)
                return None
        except Exception as err:
            _LOGGER.error("Error getting camera image: %s", err)
            return None

    def _get_camera_data(self):
        """Get camera data from coordinator."""
        try:
            station_data = self.coordinator.data["cameras"]["features"][0]["properties"]
            for camera in station_data.get("cameras", []):
                if camera["id"] == self._camera_id:
                    return camera
        except (KeyError, IndexError) as err:
            _LOGGER.error("Error accessing camera data: %s", err)
        return None

    @property
    def extra_state_attributes(self):
        """Return camera attributes."""
        camera_data = self._get_camera_data()
        if camera_data:
            return {
                "description": camera_data["description"],
                "update_time": camera_data["updateTime"],
                "message": camera_data.get("message"),
            }
        return {}