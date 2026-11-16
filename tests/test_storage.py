"""The per-account file: tolerant loading, the saved response, and housekeeping."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.parcel.const import DELETED_TTL, DOMAIN, PENDING_TTL
from custom_components.parcel.storage import ParcelStorage


def seed(hass_storage: dict[str, Any], entry_id: str, data: Any) -> None:
    key = f"{DOMAIN}.{entry_id}"
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": data}


async def test_a_new_account_starts_empty(hass: HomeAssistant) -> None:
    storage = ParcelStorage(hass, "new")
    await storage.async_load()
    assert storage.known == {}
    assert storage.pending == {}
    assert storage.icons == {}
    assert storage.deleted == {}
    assert not storage.initialized
    assert storage.cached_response() is None


async def test_a_damaged_file_loads_as_far_as_it_makes_sense(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Wrong shapes fall back to defaults instead of breaking setup."""
    seed(
        hass_storage,
        "odd",
        {
            "initialized": "yes",
            "known": {"ups:1": {"status": 2}, "ups:2": "not a record"},
            "icons": {"ups:1": "mdi:gift", "ups:2": 7},
            "pending": ["not", "a", "dict"],
            "deleted": None,
            "reads": [1, "2026-11-16T10:00:00+00:00"],
            "cache": "nope",
            "rate_limited_until": 5,
            "left_over_from_an_older_version": True,
        },
    )
    storage = ParcelStorage(hass, "odd")
    await storage.async_load()
    assert not storage.initialized
    assert list(storage.known) == ["ups:1"]
    assert storage.icons == {"ups:1": "mdi:gift"}
    assert storage.pending == {}
    assert storage.deleted == {}
    assert storage.data["reads"] == ["2026-11-16T10:00:00+00:00"]
    assert storage.data["adds"] == []
    assert storage.cached_response() is None
    assert storage.rate_limited_until(dt_util.utcnow()) is None
    assert "left_over_from_an_older_version" not in storage.data


async def test_the_saved_response_round_trips(hass: HomeAssistant) -> None:
    storage = ParcelStorage(hass, "cache")
    now = dt_util.utcnow()
    storage.remember_response([{"tracking_number": "1"}], now)
    assert storage.cached_response() == (now, [{"tracking_number": "1"}])
    storage.data["cache"] = {"fetched_at": "not a time", "deliveries": []}
    assert storage.cached_response() is None


async def test_old_markers_and_adds_are_forgotten(hass: HomeAssistant) -> None:
    storage = ParcelStorage(hass, "prune")
    now = dt_util.utcnow()
    storage.mark_deleted("ups:new", now - timedelta(hours=1))
    storage.mark_deleted("ups:old", now - DELETED_TTL - timedelta(minutes=1))
    storage.pending["ups:fresh"] = {
        "tracking_number": "fresh",
        "carrier_code": "ups",
        "description": "Fresh",
        "added_at": (now - timedelta(hours=2)).isoformat(),
    }
    storage.pending["ups:stale"] = {
        "tracking_number": "stale",
        "carrier_code": "ups",
        "description": "Stale",
        "added_at": (now - PENDING_TTL - timedelta(minutes=1)).isoformat(),
    }
    storage.prune(now)
    assert list(storage.deleted) == ["ups:new"]
    assert list(storage.pending) == ["ups:fresh"]


async def test_limits_count_only_the_last_hour_and_day(hass: HomeAssistant) -> None:
    storage = ParcelStorage(hass, "limits")
    now = dt_util.utcnow()
    storage.record_read(now - timedelta(minutes=61))
    storage.record_read(now - timedelta(minutes=50))
    storage.record_read(now)
    assert storage.reads_in_last_hour(now) == 2
    assert storage.minutes_until_read(now) == 11
    storage.record_add(now - timedelta(hours=25))
    storage.record_add(now)
    assert storage.adds_in_last_day(now) == 1
