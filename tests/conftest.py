"""Fixtures for MDT RWIS tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from homeassistant.const import CONF_API_KEY
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.mdt_rwis.const import (
    API_ALL_SITES,
    API_SITE_DATA,
    API_SITE_IMAGES,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

FIXTURES = Path(__file__).parent / "fixtures"
API_KEY = "test-key"
# Karst (564001): fixtures site.json and images.json are copied from a live
# payload captured 2026-10-26. Karst has no surface block, so the
# Bozeman Pass (53) fixture site_surface.json carries one to keep those
# sensors tested; its surface field names are unverified.
SITE_ID = "564001"
SURFACE_SITE_ID = "53"
IMAGE_URL = (
    "https://mdt.mt.gov/other/WebAppData/External/RRS/RWIS/Karst-North-Elev-5698.jpg"
)


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture."""
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    return


@pytest.fixture(autouse=True)
def us_units(hass):
    """MDT reports US units; skip HA's metric conversion in assertions."""
    hass.config.units = US_CUSTOMARY_SYSTEM


def make_entry(site_id: str, name: str) -> MockConfigEntry:
    """A configured site entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Montana DOT RWIS - {name}",
        unique_id=f"{DOMAIN}_{site_id}",
        data={CONF_API_KEY: API_KEY, CONF_SITE_ID: site_id},
        options={CONF_UPDATE_INTERVAL: 15},
    )


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Karst, the site with the live-captured payload."""
    return make_entry(SITE_ID, "Karst")


@pytest.fixture
def surface_entry() -> MockConfigEntry:
    """Bozeman Pass, the fixture with a surface block."""
    return make_entry(SURFACE_SITE_ID, "Bozeman Pass")


def mock_api(
    aioclient_mock: AiohttpClientMocker,
    *,
    site: dict[str, Any] | None = None,
    images: dict[str, Any] | None = None,
    status: int = 200,
) -> None:
    """Register responses for every MDT endpoint."""
    aioclient_mock.get(
        API_ALL_SITES, json=load_fixture("sites.json"), status=status
    )
    aioclient_mock.get(
        API_SITE_DATA,
        json=load_fixture("site.json") if site is None else site,
        status=status,
    )
    aioclient_mock.get(
        API_SITE_IMAGES,
        json=load_fixture("images.json") if images is None else images,
        status=status,
    )
    aioclient_mock.get(IMAGE_URL, content=b"jpegbytes")
