"""Config flow tests."""

from __future__ import annotations

from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mdt_rwis.const import (
    API_ALL_SITES,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from .conftest import API_KEY, SITE_ID, load_fixture, mock_api


async def test_user_to_site(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Key step leads to a sorted site picker, then an entry."""
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "site"
    selector = result["data_schema"].schema[CONF_SITE_ID]
    labels = [opt["label"] for opt in selector.config["options"]]
    assert labels == ["Bad Pass", "Bozeman Pass", "Homestake Pass"]

    # The key goes in the query string, never in a hand-built URL.
    _, url, _, _ = aioclient_mock.mock_calls[0]
    assert url.query["apiKey"] == API_KEY

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SITE_ID: SITE_ID}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Montana DOT RWIS - Bozeman Pass"
    assert result["data"] == {CONF_API_KEY: API_KEY, CONF_SITE_ID: SITE_ID}
    assert result["options"] == {CONF_UPDATE_INTERVAL: 15}
    assert result["result"].unique_id == f"{DOMAIN}_{SITE_ID}"


async def test_invalid_auth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 shows invalid_auth and keeps the form open."""
    aioclient_mock.get(API_ALL_SITES, status=401)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A network error shows cannot_connect."""
    aioclient_mock.get(API_ALL_SITES, exc=ClientError())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_timeout(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A timeout shows cannot_connect."""
    aioclient_mock.get(API_ALL_SITES, exc=TimeoutError())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_server_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A non-200, non-401 status shows cannot_connect."""
    aioclient_mock.get(API_ALL_SITES, status=500)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_existing_key_prefilled(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """A second site shows the key form prefilled, and hides configured sites."""
    mock_entry.add_to_hass(hass)
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    key_marker = next(iter(result["data_schema"].schema))
    assert key_marker.description == {"suggested_value": API_KEY}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    selector = result["data_schema"].schema[CONF_SITE_ID]
    values = [opt["value"] for opt in selector.config["options"]]
    assert SITE_ID not in values


async def test_unexpected_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Malformed data maps to unknown, not a crash."""
    aioclient_mock.get(API_ALL_SITES, exc=RuntimeError("boom"))
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["errors"] == {"base": "unknown"}


async def test_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """Reauth stores the new key on this entry and its siblings."""
    mock_entry.add_to_hass(hass)
    sibling = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}_12",
        data={CONF_API_KEY: API_KEY, CONF_SITE_ID: "12"},
    )
    sibling.add_to_hass(hass)
    aioclient_mock.get(API_ALL_SITES, json=load_fixture("sites.json"))

    result = await mock_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data[CONF_API_KEY] == "new-key"
    assert sibling.data[CONF_API_KEY] == "new-key"


async def test_reauth_invalid(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """A rejected new key keeps the reauth form open."""
    mock_entry.add_to_hass(hass)
    aioclient_mock.get(API_ALL_SITES, status=401)
    result = await mock_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "still-bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert mock_entry.data[CONF_API_KEY] == API_KEY


async def test_options_flow(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """The options flow stores the interval."""
    mock_api(aioclient_mock)
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_INTERVAL: 30}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_entry.options == {CONF_UPDATE_INTERVAL: 30}
    assert mock_entry.runtime_data.update_interval.total_seconds() == 30 * 60
