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
SITE_ID = "53"


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


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """A configured site entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Montana DOT RWIS - Bozeman Pass",
        unique_id=f"{DOMAIN}_{SITE_ID}",
        data={CONF_API_KEY: API_KEY, CONF_SITE_ID: SITE_ID},
        options={CONF_UPDATE_INTERVAL: 15},
    )


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
    aioclient_mock.get(
        "https://app.mdt.mt.gov/atms/public/camera/5301.jpg", content=b"jpegbytes"
    )
