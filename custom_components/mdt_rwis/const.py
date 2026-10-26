"""Constants for the MDT RWIS integration."""

from __future__ import annotations

DOMAIN = "mdt_rwis"
NAME = "Montana DOT RWIS"
MANUFACTURER = "Montana DOT"

CONF_SITE_ID = "site_id"
CONF_UPDATE_INTERVAL = "update_interval"

API_BASE_URL = "https://app.mdt.mt.gov/atms/api/conditions/v1"
API_ALL_SITES = f"{API_BASE_URL}/current"
API_SITE_DATA = f"{API_BASE_URL}/current/site"
API_SITE_IMAGES = f"{API_BASE_URL}/current/images/site"
API_HEADERS = {"accept": "application/json"}
API_TIMEOUT = 15

# Camera image URLs come from the API response, so only fetch from MDT hosts.
ALLOWED_IMAGE_HOST_SUFFIX = ".mt.gov"

# MDT collects RWIS data every 15 minutes.
DEFAULT_UPDATE_INTERVAL = 15
MIN_UPDATE_INTERVAL = 5
MAX_UPDATE_INTERVAL = 60

ATTRIBUTION = "Data provided by Montana DOT"
