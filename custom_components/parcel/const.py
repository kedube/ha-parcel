"""Constants for the Parcel integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "parcel"

# Parcel's documented API (https://parcel.app/help/api.html)
API_BASE: Final = "https://api.parcel.app/external"
DELIVERIES_URL: Final = f"{API_BASE}/deliveries/"
ADD_DELIVERY_URL: Final = f"{API_BASE}/add-delivery/"
CARRIERS_URL: Final = f"{API_BASE}/supported_carriers.json"

# Parcel's own web app (web.parcelapp.net). Not part of the documented API; used
# only for deleting packages, which the documented API can't do.
WEB_BASE: Final = "https://web.parcelapp.net"
WEB_DELETE_URL: Final = f"{WEB_BASE}/delete-ajax.php"
WEB_LIST_URL: Final = f"{WEB_BASE}/download-ajax.php"
WEB_COOKIE: Final = "account_token"
WEB_AUTH_ERROR: Final = "failed_verification"
# Parcel's carrier code for a placeholder package, which Parcel gives a number of its own.
PLACEHOLDER_CARRIER: Final = "pholder"

API_KEY_DOCS_URL: Final = "https://github.com/kedube/ha-parcel#get-your-parcel-api-key"
WEB_SIGN_IN_DOCS_URL: Final = (
    "https://github.com/kedube/ha-parcel#let-home-assistant-delete-packages"
)
PARCEL_WEB_URL: Final = WEB_BASE

# Entry data, besides the API key: a random secret, made once per account, that the
# unique IDs of package sensors are derived from (see entity.package_id).
CONF_PACKAGE_ID_SECRET: Final = "package_id_secret"

# Options
CONF_ACCOUNT_TOKEN: Final = "account_token"
# When the web sign-in token was entered, so we can warn before it expires.
CONF_ACCOUNT_TOKEN_SET_AT: Final = "account_token_set_at"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_PACKAGE_SENSORS: Final = "package_sensors"
# Options form only: a switch to forget the saved web sign-in. Never stored.
CONF_REMOVE_ACCOUNT_TOKEN: Final = "remove_account_token"

# Parcel's web sign-in cookie lasts 360 days (Max-Age=31104000) and isn't renewed
# on use, so the integration warns ahead of time and re-checks it daily.
WEB_TOKEN_LIFETIME: Final = timedelta(days=360)
WEB_TOKEN_WARN_AHEAD: Final = timedelta(days=14)
WEB_SIGN_IN_CHECK_INTERVAL: Final = timedelta(hours=24)
WEB_SIGN_IN_FIRST_CHECK: Final = timedelta(seconds=30)

DEFAULT_SCAN_MINUTES: Final = 10
MIN_SCAN_MINUTES: Final = 4
MAX_SCAN_MINUTES: Final = 60

# Parcel's limits: 20 reads an hour and 20 adds a day (failed adds count too).
READS_PER_HOUR: Final = 20
MANUAL_REFRESH_RESERVE: Final = 2  # keep a couple of reads for scheduled checks
MANUAL_REFRESH_MIN_GAP: Final = timedelta(seconds=60)
ADDS_PER_DAY: Final = 20
RATE_LIMIT_BACKOFF: Final = timedelta(minutes=20)
# The longest pause a Retry-After from Parcel can ask for; its limits reset hourly.
RATE_LIMIT_MAX_PAUSE: Final = timedelta(hours=2)
# When a check fails (Parcel unreachable), the last known packages stay on show for
# this long, or for this many check intervals if that is longer.
OUTAGE_GRACE: Final = timedelta(minutes=30)
OUTAGE_GRACE_CHECKS: Final = 3
# After the carrier list fails to download, wait this long before trying again.
CARRIER_RETRY_AFTER: Final = timedelta(minutes=10)
FOLLOW_UP_REFRESH_SECONDS: Final = 120

# How long things are remembered
PENDING_TTL: Final = timedelta(hours=24)
DELETED_TTL: Final = timedelta(hours=12)
DELIVERED_SENSOR_RETENTION: Final = timedelta(days=2)
CARRIER_LIST_MAX_AGE: Final = timedelta(days=1)

STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1

# Bus event fired for every package change; device triggers listen to it.
EVENT_PACKAGE_UPDATE: Final = "parcel_package_update"

EVENT_ADDED: Final = "added"
EVENT_LABEL_CREATED: Final = "label_created"
EVENT_IN_TRANSIT: Final = "in_transit"
EVENT_OUT_FOR_DELIVERY: Final = "out_for_delivery"
EVENT_READY_FOR_PICKUP: Final = "ready_for_pickup"
EVENT_DELIVERED: Final = "delivered"
EVENT_NEEDS_ATTENTION: Final = "needs_attention"
EVENT_UPDATE: Final = "update"
EVENT_REMOVED: Final = "removed"

EVENT_TYPES: Final = [
    EVENT_ADDED,
    EVENT_LABEL_CREATED,
    EVENT_IN_TRANSIT,
    EVENT_OUT_FOR_DELIVERY,
    EVENT_READY_FOR_PICKUP,
    EVENT_DELIVERED,
    EVENT_NEEDS_ATTENTION,
    EVENT_UPDATE,
    EVENT_REMOVED,
]

# Longest text accepted for a new package. Generous: they only stop runaway input
# from being sent to Parcel, where a rejected add still counts toward the day's 20.
MAX_NUMBER_LENGTH: Final = 100
MAX_NAME_LENGTH: Final = 200

# Sidebar panel
PANEL_URL: Final = "packages"
PANEL_TITLE: Final = "Packages"
PANEL_ICON: Final = "mdi:package-variant-closed"
PANEL_ELEMENT: Final = "parcel-packages-panel"
STATIC_URL: Final = "/parcel_static"

# hass.data keys
DATA_CARRIERS: Final = f"{DOMAIN}_carriers"
DATA_PANEL: Final = f"{DOMAIN}_panel"
DATA_PANEL_LOCK: Final = f"{DOMAIN}_panel_lock"
DATA_STATIC: Final = f"{DOMAIN}_static"
DATA_SUBSCRIBERS: Final = f"{DOMAIN}_subscribers"
DATA_WEB_SESSION: Final = f"{DOMAIN}_web_session"
