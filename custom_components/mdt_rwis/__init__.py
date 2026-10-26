"""The MDT RWIS integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .coordinator import MdtRwisConfigEntry, MdtRwisCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.CAMERA]


async def async_setup_entry(hass: HomeAssistant, entry: MdtRwisConfigEntry) -> bool:
    """Set up MDT RWIS from a config entry."""
    coordinator = MdtRwisCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    await _async_migrate_sensor_unique_ids(hass, entry, coordinator)

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _remove_stale_devices(hass, entry, coordinator.site_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MdtRwisConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_migrate_sensor_unique_ids(
    hass: HomeAssistant, entry: MdtRwisConfigEntry, coordinator: MdtRwisCoordinator
) -> None:
    """Rekey sensors from the GeoJSON feature id to the configured site id.

    Before 2.0 sensor unique_ids used the feature "id" from the payload. If
    that differs from the siteId stored in the entry, move them so history
    and entity_ids carry over.
    """
    old_prefix = coordinator.data.weather_feature.get("id")
    if old_prefix is None or str(old_prefix) == coordinator.site_id:
        return
    old_prefix = f"{old_prefix}_"
    new_prefix = f"{coordinator.site_id}_"

    @callback
    def _update(reg_entry: er.RegistryEntry) -> dict[str, str] | None:
        if reg_entry.domain != Platform.SENSOR:
            return None
        if not reg_entry.unique_id.startswith(old_prefix):
            return None
        new_id = new_prefix + reg_entry.unique_id.removeprefix(old_prefix)
        _LOGGER.debug("Migrating unique_id %s -> %s", reg_entry.unique_id, new_id)
        return {"new_unique_id": new_id}

    await er.async_migrate_entries(hass, entry.entry_id, _update)


@callback
def _remove_stale_devices(
    hass: HomeAssistant, entry: MdtRwisConfigEntry, site_id: str
) -> None:
    """Drop empty devices left from before sensors and cameras shared one."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if (DOMAIN, site_id) in device.identifiers:
            continue
        if er.async_entries_for_device(ent_reg, device.id, include_disabled_entities=True):
            continue
        dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
