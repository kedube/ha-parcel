"""What the integration remembers per Parcel account."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, TypedDict, cast

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DELETED_TTL, DOMAIN, PENDING_TTL, STORAGE_MINOR_VERSION, STORAGE_VERSION

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


class KnownPackage(TypedDict):
    """What was last seen for a package Parcel lists, to notice changes."""

    status: int
    first_seen: str
    delivered_at: str | None
    event: str  # signature of the latest carrier update
    description: str
    tracking_number: str
    carrier_code: str


class PendingRecord(TypedDict):
    """A package added from Home Assistant that Parcel hasn't listed yet."""

    tracking_number: str
    carrier_code: str
    description: str
    added_at: str


class CacheRecord(TypedDict):
    """Parcel's last deliveries response, reused after a restart."""

    fetched_at: str
    deliveries: list[dict[str, Any]]


class StoredState(TypedDict):
    """Everything in an account's file. Keys are package keys ("carrier:number")."""

    initialized: bool
    known: dict[str, KnownPackage]
    icons: dict[str, str]  # icons chosen by a person
    pending: dict[str, PendingRecord]
    deleted: dict[str, str]  # when each was deleted, so Parcel's cached list can't bring it back
    reads: list[str]  # times of deliveries requests in the last hour
    adds: list[str]  # times of add requests in the last day
    cache: CacheRecord | None
    rate_limited_until: str | None  # Parcel said slow down: no requests before this


def _empty() -> StoredState:
    return {
        "initialized": False,
        "known": {},
        "icons": {},
        "pending": {},
        "deleted": {},
        "reads": [],
        "adds": [],
        "cache": None,
        "rate_limited_until": None,
    }


def _coerce(stored: dict[str, Any]) -> StoredState:
    """Defaults for anything missing, and for anything that isn't the expected shape."""

    def records(name: str) -> dict[str, Any]:
        value = stored.get(name)
        if not isinstance(value, dict):
            return {}
        return {key: item for key, item in value.items() if isinstance(key, str)}

    def stamps(name: str) -> list[str]:
        value = stored.get(name)
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

    cache = stored.get("cache")
    until = stored.get("rate_limited_until")
    return {
        "initialized": stored.get("initialized") is True,
        "known": {
            key: cast(KnownPackage, item)
            for key, item in records("known").items()
            if isinstance(item, dict)
        },
        "icons": {key: item for key, item in records("icons").items() if isinstance(item, str)},
        "pending": {
            key: cast(PendingRecord, item)
            for key, item in records("pending").items()
            if isinstance(item, dict)
        },
        "deleted": {key: item for key, item in records("deleted").items() if isinstance(item, str)},
        "reads": stamps("reads"),
        "adds": stamps("adds"),
        "cache": cast(CacheRecord, cache) if isinstance(cache, dict) else None,
        "rate_limited_until": until if isinstance(until, str) else None,
    }


def _within(stamps: list[str], now: datetime, window: timedelta) -> list[str]:
    keep: list[str] = []
    for stamp in stamps:
        parsed = dt_util.parse_datetime(stamp)
        if parsed and now - parsed < window:
            keep.append(stamp)
    return keep


class _ParcelStore(Store[dict[str, Any]]):
    """The file itself. Upgrades from older layouts happen here."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        # No layout has changed yet. When one does, raise STORAGE_MINOR_VERSION and
        # convert old_data here; anything missing is filled with defaults on load.
        return old_data


class ParcelStorage:
    """A small JSON file per account in Home Assistant's .storage folder."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Prepare the store; call async_load next."""
        self._store = _ParcelStore(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
            private=True,
            atomic_writes=True,
            minor_version=STORAGE_MINOR_VERSION,
        )
        self.data: StoredState = _empty()

    async def async_load(self) -> None:
        """Read what was saved, keeping defaults for anything missing or malformed."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self.data = _coerce(stored)

    @callback
    def async_schedule_save(self) -> None:
        """Save soon, batching several changes into one write."""
        self._store.async_delay_save(lambda: cast(dict[str, Any], self.data), 10)

    async def async_save_now(self) -> None:
        """Save immediately (used when unloading)."""
        await self._store.async_save(cast(dict[str, Any], self.data))

    async def async_remove(self) -> None:
        """Delete the file (used when the account is removed)."""
        await self._store.async_remove()

    # Packages ----------------------------------------------------------------

    @property
    def known(self) -> dict[str, KnownPackage]:
        """Packages Parcel listed at the last check, by key."""
        return self.data["known"]

    @property
    def icons(self) -> dict[str, str]:
        """Icons people chose, by package key."""
        return self.data["icons"]

    @property
    def pending(self) -> dict[str, PendingRecord]:
        """Adds Parcel hasn't listed yet, by key."""
        return self.data["pending"]

    @property
    def deleted(self) -> dict[str, str]:
        """Packages deleted from Home Assistant, with when."""
        return self.data["deleted"]

    @property
    def initialized(self) -> bool:
        """Whether a first check has happened (before it, nothing is announced)."""
        return bool(self.data["initialized"])

    def mark_initialized(self) -> None:
        """Note that the first check is done."""
        self.data["initialized"] = True

    def mark_deleted(self, key: str, now: datetime) -> None:
        """Hide a package Parcel may keep listing for a while after a delete."""
        self.data["deleted"][key] = now.isoformat()

    # Parcel's last response --------------------------------------------------

    def remember_response(self, deliveries: list[dict[str, Any]], now: datetime) -> None:
        """Keep Parcel's response so a restart doesn't have to ask again."""
        self.data["cache"] = {"fetched_at": now.isoformat(), "deliveries": deliveries}

    def cached_response(self) -> tuple[datetime, list[dict[str, Any]]] | None:
        """The saved response and when it was fetched, if there is a usable one."""
        cache = self.data["cache"]
        if not cache:
            return None
        fetched_at = dt_util.parse_datetime(str(cache.get("fetched_at") or ""))
        deliveries = cache.get("deliveries")
        if fetched_at is None or not isinstance(deliveries, list):
            return None
        return fetched_at, deliveries

    # Parcel's limits ---------------------------------------------------------

    def record_read(self, now: datetime) -> None:
        """Note a deliveries request."""
        self.data["reads"] = [*_within(self.data["reads"], now, HOUR), now.isoformat()]

    def reads_in_last_hour(self, now: datetime) -> int:
        """Requests counted against Parcel's 20 an hour."""
        return len(_within(self.data["reads"], now, HOUR))

    def minutes_until_read(self, now: datetime) -> int:
        """Minutes until the oldest counted request leaves the hour window."""
        stamps = [dt_util.parse_datetime(s) for s in _within(self.data["reads"], now, HOUR)]
        oldest = min((s for s in stamps if s), default=None)
        if oldest is None:
            return 0
        return max(1, int(((oldest + HOUR) - now).total_seconds() // 60) + 1)

    def record_add(self, now: datetime) -> None:
        """Note an add request (Parcel counts failed ones too)."""
        self.data["adds"] = [*_within(self.data["adds"], now, DAY), now.isoformat()]

    def adds_in_last_day(self, now: datetime) -> int:
        """Requests counted against Parcel's 20 adds a day."""
        return len(_within(self.data["adds"], now, DAY))

    def rate_limited_until(self, now: datetime) -> datetime | None:
        """When Parcel's slow-down ends, if one is still in effect."""
        until = dt_util.parse_datetime(self.data["rate_limited_until"] or "")
        return until if until and until > now else None

    def set_rate_limited_until(self, until: datetime | None) -> None:
        """Remember (or clear) Parcel's slow-down, so restarts don't ask again early."""
        self.data["rate_limited_until"] = until.isoformat() if until else None

    # Housekeeping ------------------------------------------------------------

    def prune(self, now: datetime) -> None:
        """Forget deletes and pending adds that are old enough not to matter."""
        self.data["deleted"] = {
            key: stamp
            for key, stamp in self.data["deleted"].items()
            if (parsed := dt_util.parse_datetime(stamp)) and now - parsed < DELETED_TTL
        }
        self.data["pending"] = {
            key: item
            for key, item in self.data["pending"].items()
            if (parsed := dt_util.parse_datetime(item.get("added_at", "")))
            and now - parsed < PENDING_TTL
        }
