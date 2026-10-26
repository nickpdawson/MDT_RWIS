"""Small client for the MDT ATMS conditions API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from homeassistant.exceptions import HomeAssistantError

from .const import (
    API_ALL_SITES,
    API_HEADERS,
    API_SITE_DATA,
    API_SITE_IMAGES,
    API_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """The API could not be reached or returned an unexpected response."""


class InvalidAuth(HomeAssistantError):
    """The API rejected the key."""


async def _get(
    session: ClientSession, url: str, params: dict[str, str]
) -> dict[str, Any]:
    # The key travels in params so it never appears in a logged URL string.
    _LOGGER.debug("GET %s siteId=%s", url, params.get("siteId", "-"))
    try:
        async with asyncio.timeout(API_TIMEOUT):
            async with session.get(url, params=params, headers=API_HEADERS) as resp:
                if resp.status == 401:
                    raise InvalidAuth
                if resp.status != 200:
                    raise CannotConnect(f"HTTP {resp.status} from {url}")
                data = await resp.json(content_type=None)
    except (ClientError, TimeoutError) as err:
        raise CannotConnect(f"{type(err).__name__} from {url}") from err
    except ValueError as err:
        raise CannotConnect(f"Invalid JSON from {url}") from err
    if not isinstance(data, dict):
        raise CannotConnect(f"Unexpected payload from {url}")
    return data


def features(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the GeoJSON feature list, or an empty list."""
    items = payload.get("features")
    if not isinstance(items, list):
        return []
    return [f for f in items if isinstance(f, dict)]


def properties(feature: dict[str, Any] | None) -> dict[str, Any]:
    """Return a feature's properties dict, or an empty dict."""
    if not feature:
        return {}
    props = feature.get("properties")
    return props if isinstance(props, dict) else {}


async def async_get_sites(session: ClientSession, api_key: str) -> dict[str, str]:
    """Return {site_id: site_name} for every site the key can see."""
    data = await _get(session, API_ALL_SITES, {"apiKey": api_key})
    sites: dict[str, str] = {}
    for feature in features(data):
        props = properties(feature)
        site_id = props.get("id", feature.get("id"))
        if site_id is None:
            continue
        sites[str(site_id)] = str(props.get("name") or site_id)
    return sites


async def async_get_site(
    session: ClientSession, api_key: str, site_id: str
) -> dict[str, Any]:
    """Return current conditions for one site."""
    return await _get(session, API_SITE_DATA, {"siteId": site_id, "apiKey": api_key})


async def async_get_site_images(
    session: ClientSession, api_key: str, site_id: str
) -> dict[str, Any]:
    """Return current camera images for one site."""
    return await _get(
        session, API_SITE_IMAGES, {"siteId": site_id, "apiKey": api_key}
    )
