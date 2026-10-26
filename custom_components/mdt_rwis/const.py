"""Constants for MDT RWIS integration."""

DOMAIN = "mdt_rwis"
NAME = "Montana DOT RWIS"

# Configuration
CONF_API_KEY = "api_key"
CONF_SITE_ID = "site_id"
CONF_UPDATE_INTERVAL = "update_interval"

# Specific API Endpoints
API_BASE_URL = "https://app.mdt.mt.gov/atms/api/conditions/v1"
API_ALL_SITES = f"{API_BASE_URL}/current?apiKey={{api_key}}"
API_SITE_DATA = f"{API_BASE_URL}/current/site?siteId={{site_id}}&apiKey={{api_key}}"
API_SITE_IMAGES = f"{API_BASE_URL}/current/images/site?siteId={{site_id}}&apiKey={{api_key}}"

# Headers
API_HEADERS = {
    "accept": "application/json"
}

# Defaults
DEFAULT_UPDATE_INTERVAL = 15  # minutes
MIN_UPDATE_INTERVAL = 1
MAX_UPDATE_INTERVAL = 60


# Device class and units for various sensors
SENSOR_TYPES = {
    "air_temperature": {
        "name": "Air Temperature",
        "unit": "°F",
        "device_class": "temperature",
    },
    "dewpoint_temperature": {
        "name": "Dewpoint Temperature",
        "unit": "°F",
        "device_class": "temperature",
    },
    "relative_humidity": {
        "name": "Relative Humidity",
        "unit": "%",
        "device_class": "humidity",
    },
    "wind_speed": {
        "name": "Wind Speed",
        "unit": "mph",
        "device_class": "speed",
    },
    "wind_gust": {
        "name": "Wind Gust",
        "unit": "mph",
        "device_class": "speed",
    },
    "precip_rate": {
        "name": "Precipitation Rate",
        "unit": "in/h",
        "device_class": "precipitation",
    },
    "precip_accumulated": {
        "name": "Accumulated Precipitation",
        "unit": "in",
        "device_class": "precipitation",
    },
    "surface_temperature": {
        "name": "Surface Temperature",
        "unit": "°F",
        "device_class": "temperature",
    },
    "surface_condition": {
        "name": "Surface Condition",
        "unit": None,
        "device_class": "condition",
    }
}

# Attribution
ATTRIBUTION = "Data provided by Montana DOT"