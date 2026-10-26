"""Setup, unload, device and unique_id tests."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.mdt_rwis.const import DOMAIN
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from .conftest import SITE_ID, SURFACE_SITE_ID, load_fixture, mock_api


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """Entry loads from the live Karst payload, creates entities, and unloads."""
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)
    assert mock_entry.state is ConfigEntryState.LOADED

    assert hass.states.get("sensor.rwis_karst_air_temperature").state == "55"
    assert hass.states.get("sensor.rwis_karst_dew_point").state == "31"
    assert hass.states.get("sensor.rwis_karst_humidity").state == "38"
    assert hass.states.get("sensor.rwis_karst_wind_speed").state == "6"
    gust = hass.states.get("sensor.rwis_karst_wind_gust")
    assert gust.state == "11"
    assert gust.attributes["unit_of_measurement"] == "mph"
    assert hass.states.get("camera.rwis_karst_karst_north_elev_5698") is not None

    assert await hass.config_entries.async_unload(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.NOT_LOADED


async def test_live_payload_text_and_null_fields(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """Karst's text wind direction, precip text, nulls and observation time."""
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)

    # "Compass Degree" with a text value stays plain text.
    wind_dir = hass.states.get("sensor.rwis_karst_wind_direction")
    assert wind_dir.state == "S/SE"
    assert "device_class" not in wind_dir.attributes
    assert "unit_of_measurement" not in wind_dir.attributes
    assert "state_class" not in wind_dir.attributes

    precip_type = hass.states.get("sensor.rwis_karst_precipitation_type")
    assert precip_type.state == "No Precipitation"
    assert "device_class" not in precip_type.attributes
    precip_intensity = hass.states.get("sensor.rwis_karst_precipitation_intensity")
    assert precip_intensity.state == "No Precipitation"
    assert "unit_of_measurement" not in precip_intensity.attributes

    # precipRate is null but always created; precipAccumulated is null and
    # optional, so it is skipped. No surface block means no surface sensors.
    assert hass.states.get("sensor.rwis_karst_precipitation_rate").state == "unknown"
    assert hass.states.get("sensor.rwis_karst_accumulated_precipitation") is None
    assert hass.states.get("sensor.rwis_karst_surface_temperature") is None
    assert hass.states.get("sensor.rwis_karst_surface_condition") is None

    observed = hass.states.get("sensor.rwis_karst_observation_time")
    assert observed.attributes["device_class"] == "timestamp"
    assert dt_util.parse_datetime(observed.state) == datetime.fromtimestamp(
        1793051110, tz=UTC
    )
    reg_entry = er.async_get(hass).async_get("sensor.rwis_karst_observation_time")
    assert reg_entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_surface_site_numeric_fields(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    surface_entry: MockConfigEntry,
) -> None:
    """A site with a surface block and numeric wind direction."""
    mock_api(
        aioclient_mock,
        site=load_fixture("site_surface.json"),
        images={"type": "FeatureCollection", "features": []},
    )
    await _setup(hass, surface_entry)
    assert surface_entry.state is ConfigEntryState.LOADED

    assert hass.states.get("sensor.rwis_bozeman_pass_air_temperature").state == "28.4"
    wind_dir = hass.states.get("sensor.rwis_bozeman_pass_wind_direction")
    assert wind_dir.state == "270"
    assert wind_dir.attributes["device_class"] == "wind_direction"
    assert wind_dir.attributes["unit_of_measurement"] == "°"
    assert (
        hass.states.get("sensor.rwis_bozeman_pass_surface_condition").state == "Wet"
    )
    assert (
        hass.states.get("sensor.rwis_bozeman_pass_surface_temperature").state == "30.2"
    )
    rate = hass.states.get("sensor.rwis_bozeman_pass_precipitation_rate")
    assert rate.state == "0.02"
    assert rate.attributes["unit_of_measurement"] == "in/h"
    assert (
        hass.states.get("sensor.rwis_bozeman_pass_accumulated_precipitation").state
        == "0.15"
    )
    assert hass.states.get("sensor.rwis_bozeman_pass_precipitation_type").state == (
        "Snow"
    )
    ent_reg = er.async_get(hass)
    ids = {
        e.unique_id
        for e in er.async_entries_for_config_entry(ent_reg, surface_entry.entry_id)
    }
    assert f"{SURFACE_SITE_ID}_surface_temperature" in ids


async def test_key_not_in_logged_url(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
    caplog,
) -> None:
    """Debug logging never prints the key."""
    caplog.set_level("DEBUG", logger="custom_components.mdt_rwis")
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)
    assert "test-key" not in caplog.text


async def test_empty_features_not_ready(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """No features on the first poll means retry later."""
    mock_api(aioclient_mock, site={"type": "FeatureCollection", "features": []})
    await _setup(hass, mock_entry)
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """A 401 during setup starts a reauth flow."""
    mock_api(aioclient_mock, status=401)
    await _setup(hass, mock_entry)
    assert mock_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == SOURCE_REAUTH for f in flows)


async def test_missing_fields_do_not_crash(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """A site with no atmos, surface or cameras still loads."""
    site = load_fixture("site.json")
    site["features"][0]["properties"] = {"id": SITE_ID, "name": "Karst"}
    images = {"type": "FeatureCollection", "features": []}
    mock_api(aioclient_mock, site=site, images=images)
    await _setup(hass, mock_entry)
    assert mock_entry.state is ConfigEntryState.LOADED
    temp = hass.states.get("sensor.rwis_karst_air_temperature")
    assert temp.state == "unknown"
    assert hass.states.get("sensor.rwis_karst_surface_condition") is None
    assert hass.states.get("sensor.rwis_karst_observation_time") is None


async def test_poll_error_marks_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """A later empty payload makes entities unavailable instead of raising."""
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)
    aioclient_mock.clear_requests()
    mock_api(aioclient_mock, site={"features": []})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=16))
    await hass.async_block_till_done()
    state = hass.states.get("sensor.rwis_karst_air_temperature")
    assert state.state == "unavailable"


async def test_sensor_and_camera_share_device(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """All entities for a site sit on one device keyed by site id."""
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_reg, mock_entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, SITE_ID)}
    assert device.name == "RWIS Karst"

    entries = er.async_entries_for_config_entry(ent_reg, mock_entry.entry_id)
    domains = {e.domain for e in entries}
    assert domains == {"sensor", "camera"}
    assert all(e.device_id == device.id for e in entries)


async def test_unique_ids_kept(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """1.x unique_ids are unchanged when the feature id equals the site id."""
    mock_api(aioclient_mock)
    await _setup(hass, mock_entry)
    ent_reg = er.async_get(hass)
    ids = {
        e.unique_id
        for e in er.async_entries_for_config_entry(ent_reg, mock_entry.entry_id)
    }
    for suffix in (
        "temperature",
        "humidity",
        "wind_speed",
        "wind_direction",
        "dew_point",
        "precip_rate",
        "precip_type",
        "precip_intensity",
        "observation_time",
    ):
        assert f"{SITE_ID}_{suffix}" in ids
    assert "rwis_camera_564010" in ids


async def test_unique_id_migration_from_feature_id(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """Sensors keyed on a different feature id move to the site id."""
    site = load_fixture("site.json")
    site["features"][0]["id"] = "feature-564001"
    mock_api(aioclient_mock, site=site)

    mock_entry.add_to_hass(hass)
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    old_device = dev_reg.async_get_or_create(
        config_entry_id=mock_entry.entry_id,
        identifiers={(DOMAIN, "feature-564001")},
        name="RWIS Karst",
    )
    old = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        "feature-564001_temperature",
        config_entry=mock_entry,
        device_id=old_device.id,
        suggested_object_id="rwis_karst_temperature",
    )

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    migrated = ent_reg.async_get(old.entity_id)
    assert migrated.unique_id == f"{SITE_ID}_temperature"
    assert hass.states.get(old.entity_id).state == "55"
    assert dev_reg.async_get(old_device.id) is None


async def test_diagnostics_redacts_key(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_entry: MockConfigEntry,
) -> None:
    """Diagnostics never include the key."""
    from custom_components.mdt_rwis.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    images = copy.deepcopy(load_fixture("images.json"))
    images["apiKey"] = "test-key"
    mock_api(aioclient_mock, images=images)
    await _setup(hass, mock_entry)
    diag = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert "test-key" not in str(diag)
    assert diag["entry"]["data"]["api_key"] == "**REDACTED**"
