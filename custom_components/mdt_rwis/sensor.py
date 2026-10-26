"""Sensor platform for the MDT RWIS integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MdtRwisConfigEntry, MdtRwisCoordinator, SiteData
from .entity import MdtRwisEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def _reading(block: dict[str, Any], field: str) -> Any:
    """Return block[field]["value"], or None if any level is missing."""
    item = block.get(field)
    if isinstance(item, dict):
        return item.get("value")
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class MdtRwisSensorDescription(SensorEntityDescription):
    """Describes one RWIS reading.

    unique_suffix keeps the pre-2.0 unique_id tail so history carries over.
    always_create is set for the sensors 1.x always made; the others are only
    added when the site reports that field.
    """

    unique_suffix: str
    raw_value: Callable[[SiteData], Any]
    numeric: bool = True
    always_create: bool = False


SENSORS: tuple[MdtRwisSensorDescription, ...] = (
    MdtRwisSensorDescription(
        key="air_temperature",
        translation_key="air_temperature",
        unique_suffix="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "airTemperature"),
        always_create=True,
    ),
    MdtRwisSensorDescription(
        key="dew_point",
        translation_key="dew_point",
        unique_suffix="dew_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "dewpointTemperature"),
        always_create=True,
    ),
    MdtRwisSensorDescription(
        key="humidity",
        unique_suffix="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "relativeHumidity"),
        always_create=True,
    ),
    MdtRwisSensorDescription(
        key="wind_speed",
        unique_suffix="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "windSpeed"),
        always_create=True,
    ),
    MdtRwisSensorDescription(
        key="wind_gust",
        translation_key="wind_gust",
        unique_suffix="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "windGust"),
    ),
    MdtRwisSensorDescription(
        key="wind_direction",
        translation_key="wind_direction",
        unique_suffix="wind_direction",
        raw_value=lambda d: _reading(d.atmos, "windDirection"),
        always_create=True,
    ),
    MdtRwisSensorDescription(
        key="precip_rate",
        translation_key="precip_rate",
        unique_suffix="precip_rate",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.INCHES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "precipRate"),
        always_create=True,
    ),
    MdtRwisSensorDescription(
        key="precip_accumulated",
        translation_key="precip_accumulated",
        unique_suffix="precip_accumulated",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.atmos, "precipAccumulated"),
    ),
    MdtRwisSensorDescription(
        key="surface_temperature",
        translation_key="surface_temperature",
        unique_suffix="surface_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        raw_value=lambda d: _reading(d.surface, "surfaceTemperature"),
    ),
    MdtRwisSensorDescription(
        key="surface_condition",
        translation_key="surface_condition",
        unique_suffix="surface_condition",
        numeric=False,
        raw_value=lambda d: _reading(d.surface, "surfaceCondition"),
    ),
)

# MDT's payload has no schema, so wind direction may be degrees or a
# compass label. Pick the entity shape from the first reading.
WIND_DIRECTION_DEGREES = MdtRwisSensorDescription(
    key="wind_direction",
    translation_key="wind_direction",
    unique_suffix="wind_direction",
    device_class=SensorDeviceClass.WIND_DIRECTION,
    native_unit_of_measurement=DEGREE,
    state_class=SensorStateClass.MEASUREMENT_ANGLE,
    raw_value=lambda d: _reading(d.atmos, "windDirection"),
    always_create=True,
)
WIND_DIRECTION_TEXT = MdtRwisSensorDescription(
    key="wind_direction",
    translation_key="wind_direction",
    unique_suffix="wind_direction",
    numeric=False,
    raw_value=lambda d: _reading(d.atmos, "windDirection"),
    always_create=True,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MdtRwisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for one site."""
    coordinator = entry.runtime_data
    entities: list[MdtRwisSensor] = []
    for description in SENSORS:
        raw = description.raw_value(coordinator.data)
        if description.key == "wind_direction":
            description = (
                WIND_DIRECTION_TEXT
                if raw is not None and _number(raw) is None
                else WIND_DIRECTION_DEGREES
            )
        elif raw is None and not description.always_create:
            _LOGGER.debug(
                "Site %s has no %s reading; skipping",
                coordinator.site_id,
                description.key,
            )
            continue
        entities.append(MdtRwisSensor(coordinator, description))
    async_add_entities(entities)


class MdtRwisSensor(MdtRwisEntity, SensorEntity):
    """One RWIS reading."""

    entity_description: MdtRwisSensorDescription

    def __init__(
        self,
        coordinator: MdtRwisCoordinator,
        description: MdtRwisSensorDescription,
    ) -> None:
        """Set up the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.site_id}_{description.unique_suffix}"

    @property
    def native_value(self) -> Any:
        """Return the current reading."""
        raw = self.entity_description.raw_value(self.coordinator.data)
        if raw is None:
            return None
        if self.entity_description.numeric:
            return _number(raw)
        return str(raw)
