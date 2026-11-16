"""What the integration remembers per Parcel account."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DELETED_TTL, DOMAIN, PENDING_TTL, STORAGE_VERSION

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def _empty() -> dict[str, Any]:
    return {
        "initialized": False,
        "known": {},  # key → status, first_seen, delivered_at, last update signature, names
        "icons": {},  # key → icon chosen by a person
        "pending": {},  # key → packages added from Home Assistant that Parcel hasn't listed yet
        "deleted": {},  # key → when it was deleted, so Parcel's cached list can't bring it back
        "reads": [],  # times of deliveries requests in the last hour
        "adds": [],  # times of add requests in the last day
        "cache": None,  # last deliveries response, reused after a restart
        "rate_limited_until": None,  # Parcel said slow down: no requests before this
    }


def _within(stamps: list[str], now: datetime, window: timedelta) -> list[str]:
    keep: list[str] = []
    for stamp in stamps:
        parsed = dt_util.parse_datetime(stamp)
        if parsed and now - parsed < window:
            keep.append(stamp)
    return keep


class ParcelStorage:
    """A small JSON file per account in Home Assistant's .storage folder."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Prepare the store; call async_load next."""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}", private=True, atomic_writes=True
        )
        self.data: dict[str, Any] = _empty()

    async def async_load(self) -> None:
        """Read what was saved, keeping defaults for anything missing."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            data = _empty()
            data.update({key: value for key, value in stored.items() if key in data})
            self.data = data

    @callback
    def async_schedule_save(self) -> None:
        """Save soon, batching several changes into one write."""
        self._store.async_delay_save(lambda: self.data, 10)

    async def async_save_now(self) -> None:
        """Save immediately (used when unloading)."""
        await self._store.async_save(self.data)

    async def async_remove(self) -> None:
        """Delete the file (used when the account is removed)."""
        await self._store.async_remove()

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
        until = dt_util.parse_datetime(self.data.get("rate_limited_until") or "")
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
