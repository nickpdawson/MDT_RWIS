"""Camera tests."""

from __future__ import annotations

import pytest

from homeassistant.components.camera import async_get_image
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.mdt_rwis.camera import is_allowed_image_url
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from .conftest import load_fixture, mock_api

CAMERA = "camera.rwis_bozeman_pass_looking_east"
IMAGE_URL = "https://app.mdt.mt.gov/atms/public/camera/5301.jpg"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _image_calls(aioclient_mock: AiohttpClientMocker) -> int:
    return sum(1 for call in aioclient_mock.mock_calls if str(call[1]) == IMAGE_URL)


async def test_image_cached_until_update_time_changes(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """Repeat requests reuse bytes until MDT posts a new image."""
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)

    image = await async_get_image(hass, CAMERA)
    assert image.content == b"jpegbytes"
    await async_get_image(hass, CAMERA)
    assert _image_calls(aioclient_mock) == 1

    images = load_fixture("images.json")
    images["features"][0]["properties"]["cameras"][0]["updateTime"] = (
        "2026-10-26T12:15:00Z"
    )
    coordinator = mock_entry.runtime_data
    aioclient_mock.clear_requests()
    mock_api(aioclient_mock, images=images)
    await coordinator.async_refresh()
    await async_get_image(hass, CAMERA)
    assert _image_calls(aioclient_mock) == 1


async def test_off_host_image_not_fetched(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """An image URL outside *.mt.gov is never requested."""
    images = load_fixture("images.json")
    images["features"][0]["properties"]["cameras"][0]["image"] = (
        "https://evil.example.com/x.jpg"
    )
    mock_api(aioclient_mock, images=images)
    aioclient_mock.get("https://evil.example.com/x.jpg", content=b"bad")
    await _setup(hass, mock_entry)

    with pytest.raises(HomeAssistantError):
        await async_get_image(hass, CAMERA)
    assert not any("evil" in str(call[1]) for call in aioclient_mock.mock_calls)


def test_allowed_hosts() -> None:
    """Only https on mt.gov hosts passes."""
    assert is_allowed_image_url("https://app.mdt.mt.gov/a.jpg")
    assert is_allowed_image_url("https://mt.gov/a.jpg")
    assert not is_allowed_image_url("http://app.mdt.mt.gov/a.jpg")
    assert not is_allowed_image_url("https://mt.gov.evil.com/a.jpg")
    assert not is_allowed_image_url("https://evilmt.gov/a.jpg")
    assert not is_allowed_image_url(None)
