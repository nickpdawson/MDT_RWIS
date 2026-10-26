"""Camera platform for the MDT RWIS integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ALLOWED_IMAGE_HOST_SUFFIX, API_TIMEOUT
from .coordinator import MdtRwisConfigEntry, MdtRwisCoordinator
from .entity import MdtRwisEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def is_allowed_image_url(url: Any) -> bool:
    """Only fetch https images from MDT hosts."""
    if not isinstance(url, str):
        return False
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and (
        host == ALLOWED_IMAGE_HOST_SUFFIX[1:] or host.endswith(ALLOWED_IMAGE_HOST_SUFFIX)
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MdtRwisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one camera entity per camera at the site."""
    coordinator = entry.runtime_data
    async_add_entities(
        MdtRwisCamera(coordinator, camera) for camera in coordinator.data.cameras
    )


class MdtRwisCamera(MdtRwisEntity, Camera):
    """Still image from an RWIS site camera."""

    def __init__(
        self, coordinator: MdtRwisCoordinator, camera: dict[str, Any]
    ) -> None:
        """Set up the camera."""
        MdtRwisEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._camera_id = camera["id"]
        self._attr_name = str(camera.get("name") or f"Camera {self._camera_id}")
        self._attr_unique_id = f"rwis_camera_{self._camera_id}"
        self._image: bytes | None = None
        self._image_time: Any = None

    def _camera(self) -> dict[str, Any] | None:
        for camera in self.coordinator.data.cameras:
            if camera["id"] == self._camera_id:
                return camera
        return None

    @property
    def available(self) -> bool:
        """Unavailable when the site stops listing this camera."""
        return super().available and self._camera() is not None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest still, fetching only when updateTime changes."""
        camera = self._camera()
        if camera is None:
            return self._image

        update_time = camera.get("updateTime")
        if self._image is not None and update_time == self._image_time:
            return self._image

        url = camera.get("image")
        if not is_allowed_image_url(url):
            _LOGGER.warning(
                "Camera %s image URL is not an https *.mt.gov address; skipping",
                self._camera_id,
            )
            return self._image

        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with session.get(url) as resp:
                    if resp.status != 200:
                        _LOGGER.debug(
                            "Camera %s image fetch returned HTTP %s",
                            self._camera_id,
                            resp.status,
                        )
                        return self._image
                    self._image = await resp.read()
        except (ClientError, TimeoutError) as err:
            _LOGGER.debug("Camera %s image fetch failed: %s", self._camera_id, err)
            return self._image

        self._image_time = update_time
        return self._image

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return camera details from MDT."""
        camera = self._camera() or {}
        return {
            "description": camera.get("description"),
            "update_time": camera.get("updateTime"),
            "message": camera.get("message"),
        }
