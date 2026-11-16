"""Diagnostics download, with keys, tokens and package details redacted."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_ACCOUNT_TOKEN
from .coordinator import ParcelConfigEntry

# account_token_set_at is a timestamp, not a secret, so it's left in for debugging.
# "event" is the carrier's own wording, which often names people and places, and
# "date_text" is a carrier's date as written when it isn't a date that can be read.
TO_REDACT = {
    CONF_API_KEY,
    CONF_ACCOUNT_TOKEN,
    "key",
    "tracking_number",
    "description",
    "extra_information",
    "event",
    "location",
    "additional",
    "date_text",
}


def _scrub(text: str | None, private: Iterable[str | None]) -> str | None:
    """The text with any of the private values in it replaced (longest first)."""
    if not text:
        return text
    for value in sorted({value for value in private if value}, key=len, reverse=True):
        text = text.replace(value, REDACTED)
    return text


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ParcelConfigEntry
) -> dict[str, Any]:
    """What's useful for troubleshooting, without personal details."""
    coordinator = entry.runtime_data
    now = dt_util.utcnow()
    data = coordinator.data
    # Parcel's error messages are passed on as they are; in case one names a package.
    private: list[str | None] = [
        entry.data.get(CONF_API_KEY),
        entry.options.get(CONF_ACCOUNT_TOKEN),
    ]
    if data:
        for delivery in data.deliveries.values():
            private += [delivery.tracking_number, delivery.description]
        for pending in data.pending.values():
            private += [pending.tracking_number, pending.description]
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "status": {
            "last_update_success": coordinator.last_update_success,
            "last_error": _scrub(coordinator.last_error, private),
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "checks_last_hour": coordinator.storage.reads_in_last_hour(now),
            "adds_last_day": coordinator.storage.adds_in_last_day(now),
            "web_sign_in_configured": coordinator.web_client is not None,
            "fetched_at": data.fetched_at.isoformat() if data and data.fetched_at else None,
            "carriers_loaded": len(coordinator.carriers.carriers),
        },
        "deliveries": [
            async_redact_data(delivery.as_dict(), TO_REDACT)
            for delivery in (data.deliveries.values() if data else [])
        ],
        "pending_count": len(data.pending) if data else 0,
    }
