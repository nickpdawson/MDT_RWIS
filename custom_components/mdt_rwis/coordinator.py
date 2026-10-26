"""Data coordinator for the MDT RWIS integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    CannotConnect,
    InvalidAuth,
    async_get_site,
    async_get_site_images,
    features,
    properties,
)
from .const import (
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type MdtRwisConfigEntry = ConfigEntry[MdtRwisCoordinator]


@dataclass
class SiteData:
    """One poll of a single RWIS site."""

    weather: dict[str, Any]
    images: dict[str, Any] | None = None
    weather_feature: dict[str, Any] = field(default_factory=dict)
    image_feature: dict[str, Any] = field(default_factory=dict)

    @property
    def station(self) -> dict[str, Any]:
        """Properties of the weather feature."""
        return properties(self.weather_feature)

    @property
    def atmos(self) -> dict[str, Any]:
        """First atmospheric sensor block."""
        return _first_dict(self.station.get("atmos"))

    @property
    def surface(self) -> dict[str, Any]:
        """First pavement sensor block."""
        return _first_dict(self.station.get("surface"))

    @property
    def cameras(self) -> list[dict[str, Any]]:
        """Camera records for the site."""
        cams = properties(self.image_feature).get("cameras")
        if not isinstance(cams, list):
            return []
        return [c for c in cams if isinstance(c, dict) and c.get("id") is not None]


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _pick_feature(payload: dict[str, Any] | None, site_id: str) -> dict[str, Any]:
    """Return the feature for site_id, else the first feature."""
    items = features(payload or {})
    for feature in items:
        if str(properties(feature).get("id", feature.get("id"))) == site_id:
            return feature
    return items[0] if items else {}


def update_interval_minutes(entry: ConfigEntry) -> int:
    """Interval from options, falling back to data for entries made before 2.0."""
    value = entry.options.get(
        CONF_UPDATE_INTERVAL,
        entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULT_UPDATE_INTERVAL
    return max(MIN_UPDATE_INTERVAL, min(MAX_UPDATE_INTERVAL, value))


class MdtRwisCoordinator(DataUpdateCoordinator[SiteData]):
    """Polls one site's conditions and camera list."""

    config_entry: MdtRwisConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MdtRwisConfigEntry) -> None:
        """Set up the coordinator for a config entry."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_SITE_ID]}",
            update_interval=timedelta(minutes=update_interval_minutes(entry)),
        )
        self.site_id: str = str(entry.data[CONF_SITE_ID])
        self._session = async_get_clientsession(hass)

    @property
    def site_name(self) -> str:
        """Station name from the payload, else the site id."""
        name = self.data.station.get("name") if self.data else None
        return str(name) if name else self.site_id

    async def _async_update_data(self) -> SiteData:
        api_key = self.config_entry.data[CONF_API_KEY]
        try:
            weather = await async_get_site(self._session, api_key, self.site_id)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("MDT rejected the API key") from err
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err

        weather_feature = _pick_feature(weather, self.site_id)
        if not weather_feature:
            raise UpdateFailed(f"No data returned for site {self.site_id}")

        # A camera outage should not take the weather sensors down with it.
        try:
            images = await async_get_site_images(self._session, api_key, self.site_id)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("MDT rejected the API key") from err
        except CannotConnect as err:
            _LOGGER.debug("Camera list fetch failed for %s: %s", self.site_id, err)
            images = self.data.images if self.data else None

        return SiteData(
            weather=weather,
            images=images,
            weather_feature=weather_feature,
            image_feature=_pick_feature(images, self.site_id),
        )
