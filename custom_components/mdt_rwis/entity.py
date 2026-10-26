"""Base entity for the MDT RWIS integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import MdtRwisCoordinator


class MdtRwisEntity(CoordinatorEntity[MdtRwisCoordinator]):
    """Ties every entity for a site to one device keyed on the site id."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: MdtRwisCoordinator) -> None:
        """Set up the shared device info."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.site_id)},
            name=f"RWIS {coordinator.site_name}",
            manufacturer=MANUFACTURER,
            model="RWIS station",
            serial_number=coordinator.site_id,
        )
