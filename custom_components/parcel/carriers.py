"""Parcel's carrier list, cached for a day and shared by all accounts."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import ParcelError, async_fetch_carriers
from .const import CARRIER_LIST_MAX_AGE, CARRIER_RETRY_AFTER, DOMAIN, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

# Extra detail some carriers need, keyed by extra_required in Parcel's list.
EXTRA_EMAIL = 2

# Longest name shown where space is tight; longer ones lose whole words, never letters.
SHORT_NAME_LENGTH = 18


class CarrierRegistry:
    """Carrier codes and names."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Set up an empty registry; call async_ensure_loaded before relying on it."""
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.carriers")
        self.carriers: dict[str, dict[str, Any]] = {}
        self._fetched_at: datetime | None = None
        self._failed_at: datetime | None = None
        self._loaded = False
        self._lock = asyncio.Lock()

    async def async_ensure_loaded(self) -> dict[str, dict[str, Any]]:
        """Load from disk, and refresh from Parcel when the copy is over a day old."""
        async with self._lock:
            if not self._loaded:
                stored = await self._store.async_load()
                if isinstance(stored, dict):
                    self.carriers = stored.get("carriers") or {}
                    self._fetched_at = dt_util.parse_datetime(stored.get("fetched_at") or "")
                self._loaded = True
            now = dt_util.utcnow()
            if self.carriers and self._fetched_at and now - self._fetched_at < CARRIER_LIST_MAX_AGE:
                return self.carriers
            if self._failed_at and now - self._failed_at < CARRIER_RETRY_AFTER:
                # The last download failed a moment ago; don't make every caller wait
                # for another try.
                return self.carriers
            try:
                carriers = await async_fetch_carriers(async_get_clientsession(self.hass))
            except ParcelError as err:
                _LOGGER.debug("Keeping the cached carrier list: %s", err)
                self._failed_at = now
                return self.carriers
            self._failed_at = None
            if carriers:
                self.carriers = carriers
                self._fetched_at = now
                await self._store.async_save({"carriers": carriers, "fetched_at": now.isoformat()})
            return self.carriers

    def name(self, code: str) -> str:
        """Display name for a carrier code."""
        info = self.carriers.get(code)
        return str(info["name"]) if info else code.upper()

    def short_name(self, code: str) -> str:
        """The name for compact places: without brackets, and whole words only.

        "Royal Mail" stays as it is; "DHL Global Mail (Germany)" becomes "DHL Global Mail".
        """
        words = self.name(code).split("(")[0].split()
        if not words:
            return code.upper()
        short = words[0]
        for word in words[1:]:
            if len(short) + 1 + len(word) > SHORT_NAME_LENGTH:
                break
            short = f"{short} {word}"
        return short

    def extra(self, code: str) -> int:
        """Which extra detail a carrier needs (0 when none)."""
        try:
            return int(self.carriers.get(code, {}).get("extra", 0))
        except (TypeError, ValueError):
            return 0
