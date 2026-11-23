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
    assert storage.delivered == {}
    assert storage.delivered_checked_at is None
    assert not storage.initialized
    assert storage.cached_response() is None


async def test_a_damaged_file_loads_as_far_as_it_makes_sense(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Wrong shapes fall back to defaults instead of breaking setup or every check."""
    whole = {
        "status": 2,
        "first_seen": "2026-11-15T10:00:00+00:00",
        "delivered_at": None,
        "event": "In transit||",
        "description": "Coffee grinder",
        "tracking_number": "1",
        "carrier_code": "ups",
    }
    seed(
        hass_storage,
        "odd",
        {
            "initialized": "yes",
            "known": {
                "ups:1": whole,
                "ups:2": "not a record",
                "ups:3": {"status": 2},  # nothing to tell which package it is
                "ups:4": {**whole, "status": [2]},
                "ups:5": {**whole, "first_seen": "2026-02-30T10:00:00+00:00"},
                "ups:6": {**whole, "tracking_number": 6},
                "ups:7": {**whole, "delivered_at": "yesterday", "event": None},
            },
            "icons": {"ups:1": "mdi:gift", "ups:2": 7},
            "pending": {
                "ups:8": {"tracking_number": 8, "carrier_code": "ups", "description": "x"},
                "ups:9": {
                    "tracking_number": "9",
                    "carrier_code": "ups",
                    "description": "x",
                    "added_at": "2026-02-30T10:00:00+00:00",
                },
            },
            "deleted": {"ups:10": "not a time", "ups:11": "2026-11-16T10:00:00+00:00"},
            "unlisted": ["not", "a", "dict"],
            "delivered": {"usps:12": {"tracking_number": "12"}, "usps:13": "not a listing"},
            "delivered_checked_at": "2026-11-16",
            "reads": [
                1,
                "2026-11-16T10:00:00+00:00",
                "2026-11-16T10:00:00",
                "2026-13-01T00:00:00+00:00",
            ],
            "cache": {"fetched_at": "2026-02-30T10:00:00+00:00", "deliveries": []},
            "rate_limited_until": "2026-11-16 25:00:00+00:00",
            "left_over_from_an_older_version": True,
        },
    )
    storage = ParcelStorage(hass, "odd")
    await storage.async_load()
    assert not storage.initialized
    assert storage.known == {
        "ups:1": whole,
        "ups:7": {**whole, "delivered_at": None, "event": ""},
    }
    assert storage.icons == {"ups:1": "mdi:gift"}
    assert storage.pending == {}
    assert storage.deleted == {"ups:11": "2026-11-16T10:00:00+00:00"}
    assert storage.unlisted == {}
    # A listing is checked when it's read back; one that can't be read is dropped then.
    assert storage.delivered == {"usps:12": {"tracking_number": "12"}}
    assert storage.delivered_checked_at is None
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
