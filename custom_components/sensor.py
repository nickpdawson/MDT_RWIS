"""Sensor platform for MDT RWIS."""
import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfSpeed,
    PERCENTAGE,
    UnitOfLength,
    DEGREE,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MDT RWIS sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    _LOGGER.debug("Setting up sensors with coordinator data: %s", coordinator.data)
    
    entities = []
    
    # Get first station data
    if coordinator.data and "features" in coordinator.data.get("weather", {}):
        station = coordinator.data["weather"]["features"][0]
        _LOGGER.debug("Found station data: %s", station)
        atmos = station["properties"].get("atmos", [{}])[0]
        _LOGGER.debug("Atmospheric data: %s", atmos)
        
        # In async_setup_entry, add them gradually:
        entities.extend([
            RWISTemperatureSensor(coordinator, station["id"]),
            RWISHumiditySensor(coordinator, station["id"]),
            RWISWindSpeedSensor(coordinator, station["id"]),
            RWISWindDirectionSensor(coordinator, station["id"]),
            RWISDewPointSensor(coordinator, station["id"]),
            RWISPrecipitationRateSensor(coordinator, station["id"]),
        ])
    else:
        _LOGGER.error("No weather data available in coordinator: %s", coordinator.data)

    async_add_entities(entities)

class RWISBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for RWIS sensors."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._station_id = station_id
        station_data = self._get_station_data()
        
        # Set basic device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station_id)},
            "name": f"RWIS {station_data['properties']['name']}",
            "manufacturer": "Montana DOT",
            "model": "RWIS Station",
        }

    def _get_station_data(self):
        """Get the station data from coordinator."""
        for feature in self.coordinator.data["weather"]["features"]:
            if feature["id"] == self._station_id:
                return feature
        return None
        
    def _get_atmos_data(self):
        """Get atmospheric data for the station."""
        station_data = self._get_station_data()
        if station_data:
            return station_data["properties"]["atmos"][0]
        return None

class RWISTemperatureSensor(RWISBaseSensor):
    """Temperature sensor for RWIS station."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        station_data = self._get_station_data()
        
        self._attr_name = f"RWIS {station_data['properties']['name']} Temperature"
        self._attr_unique_id = f"{station_id}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the temperature."""
        atmos = self._get_atmos_data()
        if atmos:
            return atmos["airTemperature"]["value"]
        return None

class RWISHumiditySensor(RWISBaseSensor):
    """Humidity sensor for RWIS station."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        station_data = self._get_station_data()
        
        self._attr_name = f"RWIS {station_data['properties']['name']} Humidity"
        self._attr_unique_id = f"{station_id}_humidity"
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the humidity."""
        atmos = self._get_atmos_data()
        if atmos:
            return atmos["relativeHumidity"]["value"]
        return None

class RWISWindSpeedSensor(RWISBaseSensor):
    """Wind speed sensor for RWIS station."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        station_data = self._get_station_data()
        
        self._attr_name = f"RWIS {station_data['properties']['name']} Wind Speed"
        self._attr_unique_id = f"{station_id}_wind_speed"
        self._attr_device_class = SensorDeviceClass.WIND_SPEED
        self._attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the wind speed."""
        atmos = self._get_atmos_data()
        if atmos:
            return atmos["windSpeed"]["value"]
        return None

class RWISWindDirectionSensor(RWISBaseSensor):
    """Wind direction sensor for RWIS station."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        station_data = self._get_station_data()
        
        self._attr_name = f"RWIS {station_data['properties']['name']} Wind Direction"
        self._attr_unique_id = f"{station_id}_wind_direction"
        # Remove state_class since direction is a string
        self._attr_state_class = None
        # Remove unit of measurement since it's compass directions
        self._attr_native_unit_of_measurement = None
        self._attr_icon = "mdi:compass"

    @property
    def native_value(self):
        """Return the wind direction."""
        atmos = self._get_atmos_data()
        if atmos:
            return atmos["windDirection"]["value"]
        return None

class RWISDewPointSensor(RWISBaseSensor):
    """Dew point sensor for RWIS station."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        station_data = self._get_station_data()
        
        self._attr_name = f"RWIS {station_data['properties']['name']} Dew Point"
        self._attr_unique_id = f"{station_id}_dew_point"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the dew point."""
        atmos = self._get_atmos_data()
        if atmos:
            return atmos["dewpointTemperature"]["value"]
        return None

class RWISPrecipitationRateSensor(RWISBaseSensor):
    """Precipitation rate sensor for RWIS station."""

    def __init__(self, coordinator, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        station_data = self._get_station_data()
        
        self._attr_name = f"RWIS {station_data['properties']['name']} Precipitation Rate"
        self._attr_unique_id = f"{station_id}_precip_rate"
        self._attr_native_unit_of_measurement = f"{UnitOfLength.INCHES}/h"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the precipitation rate."""
        atmos = self._get_atmos_data()
        if atmos:
            return atmos["precipRate"]["value"]
        return None

