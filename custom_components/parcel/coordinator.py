"""Polls Parcel, notices changes, and runs add and delete for one account."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo
import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    ParcelAuthError,
    ParcelClient,
    ParcelError,
    ParcelRateLimitError,
    ParcelRequestError,
    ParcelWebAuthError,
    ParcelWebClient,
)
from .carriers import EXTRA_EMAIL, CarrierRegistry
from .changes import REASON_DELETED, Change, detect_changes, event_message, removal
from .const import (
    ADDS_PER_DAY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_MINUTES,
    DELIVERED_CHECK_INTERVAL,
    DELIVERED_SENSOR_RETENTION,
    DOMAIN,
    EVENT_NEEDS_ATTENTION,
    EVENT_PACKAGE_UPDATE,
    FOLLOW_UP_REFRESH_SECONDS,
    MANUAL_REFRESH_MIN_GAP,
    MANUAL_REFRESH_RESERVE,
    OUTAGE_GRACE,
    OUTAGE_GRACE_CHECKS,
    RATE_LIMIT_BACKOFF,
    RATE_LIMIT_MAX_PAUSE,
    READS_PER_HOUR,
    UNLISTED_GRACE,
)
from .matching import (
    find_stored,
    lists_any,
    lists_number,
    match_pending,
    same_package,
    split_key,
    still_listed,
)
from .models import (
    DELIVERED,
    NOT_FOUND,
    STATUS_SLUGS,
    Delivery,
    by_shipment,
    detect_carriers,
    guess_icon,
    listing_key,
    normalize_number,
    package_key,
)
from .storage import ParcelStorage, PendingRecord
from .summary import Summary, build_summary
from .web_sign_in import WebSignInMonitor

_LOGGER = logging.getLogger(__name__)

type ParcelConfigEntry = ConfigEntry[ParcelCoordinator]

ICON_FORMAT = re.compile(r"^mdi:[a-z0-9-]+$")

type EventListener = Callable[[str, dict[str, Any]], None]


def _text(value: str | None) -> str | None:
    """A trimmed string, or None when there's nothing in it."""
    return (value or "").strip() or None


def _other_shipment(key: str, other: str) -> bool:
    """Whether two keys name different shipments ("@<shipment ID>") of one Amazon order."""
    first = split_key(key)[1].partition("@")[2]
    second = split_key(other)[1].partition("@")[2]
    return bool(first and second and first != second)


@dataclass(slots=True)
class PendingAdd:
    """A package added from Home Assistant that Parcel hasn't listed yet."""

    key: str
    tracking_number: str
    carrier_code: str
    description: str
    added_at: datetime

    @classmethod
    def from_store(cls, key: str, item: PendingRecord) -> PendingAdd | None:
        """Rebuild from storage."""
        added_at = dt_util.parse_datetime(item.get("added_at") or "")
        if not added_at:
            return None
        return cls(
            key=key,
            tracking_number=item.get("tracking_number", ""),
            carrier_code=item.get("carrier_code", ""),
            description=item.get("description", ""),
            added_at=added_at,
        )

    def to_store(self) -> PendingRecord:
        """Serialize for storage."""
        return {
            "tracking_number": self.tracking_number,
            "carrier_code": self.carrier_code,
            "description": self.description,
            "added_at": self.added_at.isoformat(),
        }


@dataclass(slots=True)
class ParcelSnapshot:
    """Everything known about the account after a check."""

    deliveries: dict[str, Delivery] = field(default_factory=dict)
    pending: dict[str, PendingAdd] = field(default_factory=dict)
    fetched_at: datetime | None = None
    # Delivered packages Parcel's API no longer lists, shown as it last listed them.
    kept: set[str] = field(default_factory=set)


class ParcelCoordinator(DataUpdateCoordinator[ParcelSnapshot]):
    """Keeps one Parcel account's packages current."""

    config_entry: ParcelConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ParcelConfigEntry,
        client: ParcelClient,
        storage: ParcelStorage,
        carriers: CarrierRegistry,
        web_client: ParcelWebClient | None = None,
    ) -> None:
        """Set the polling interval from the account's options."""
        minutes = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_MINUTES))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.storage = storage
        self.carriers = carriers
        self.web_sign_in = WebSignInMonitor(hass, entry, web_client)
        self.device_id: str | None = None
        self._event_listeners: list[EventListener] = []
        self._follow_up_unsub: CALLBACK_TYPE | None = None
        # Why the latest check failed, kept while the last known packages are still shown.
        self._trouble: str | None = None
        self._summary: tuple[date, Summary] | None = None
        # Adds on their way to Parcel, so a double submit doesn't spend two.
        self._adding: set[tuple[str, str]] = set()
        # Keys Parcel has listed twice, so that's logged once.
        self._duplicates: set[str] = set()
        # Kept delivered packages the web app's list left out, and when it first did.
        self._missing_from_web: dict[str, datetime] = {}

    @property
    def web_client(self) -> ParcelWebClient | None:
        """Parcel's web app for this account, when a web sign-in is configured."""
        return self.web_sign_in.client

    # Events ------------------------------------------------------------------

    @callback
    def async_add_event_listener(self, listener: EventListener) -> CALLBACK_TYPE:
        """Call listener(event_type, data) for every package change."""
        self._event_listeners.append(listener)

        @callback
        def remove() -> None:
            if listener in self._event_listeners:
                self._event_listeners.remove(listener)

        return remove

    @callback
    def _emit(self, data: dict[str, Any]) -> None:
        self.hass.bus.async_fire(EVENT_PACKAGE_UPDATE, data)
        for listener in list(self._event_listeners):
            listener(data["type"], data)

    @callback
    def _emit_all(self, events: list[dict[str, Any]]) -> None:
        for data in events:
            self._emit(data)

    def _event_data(self, change: Change) -> dict[str, Any]:
        """What the bus event, the event entity and device triggers carry for a change."""
        delivery = change.delivery
        latest = delivery.latest_event
        carrier = self.carriers.name(delivery.carrier_code)
        previous = change.previous_status
        data: dict[str, Any] = {
            "entry_id": self.config_entry.entry_id,
            "device_id": self.device_id,
            "type": change.kind,
            "key": delivery.key,
            "description": delivery.description,
            "tracking_number": delivery.tracking_number,
            "carrier_code": delivery.carrier_code,
            "carrier": carrier,
            "status": delivery.status,
            "previous_status": STATUS_SLUGS.get(previous) if previous is not None else None,
            "event": latest.text if latest else None,
            "location": latest.location if latest else None,
            "message": event_message(change.kind, delivery, carrier),
        }
        if change.reason:
            data["reason"] = change.reason
        elif change.kind == EVENT_NEEDS_ATTENTION:
            data["reason"] = delivery.status
        return data

    @callback
    def async_update_listeners(self) -> None:
        """Tell entities and the panel about a change; the summary is worked out afresh."""
        self._summary = None
        super().async_update_listeners()

    # Polling -----------------------------------------------------------------

    async def _async_update_data(self) -> ParcelSnapshot:
        now = dt_util.utcnow()
        if until := self.storage.rate_limited_until(now):
            # Parcel asked us to slow down. Asking again early (a restart, a setup
            # retry, the next poll) keeps the lockout going, so make no request.
            return self._keep_last_data("rate_limited", (until - now).total_seconds())
        if self.storage.reads_in_last_hour(now) >= READS_PER_HOUR:
            _LOGGER.debug("Skipping this check: Parcel's 20 checks an hour are used up")
            return self._keep_last_data("hourly_limit", self.storage.minutes_until_read(now) * 60)
        self.storage.record_read(now)
        try:
            raw = await self.client.async_get_deliveries()
        except ParcelAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_api_key"
            ) from err
        except ParcelRateLimitError as err:
            wait = self._pause_requests(err.retry_after)
            self._trouble = None  # Parcel answered; the pause is reported on its own
            # Write now, not after the usual delay, so a restart or setup retry sees it.
            await self.storage.async_save_now()
            return self._keep_last_data("rate_limited", wait.total_seconds(), err)
        except ParcelError as err:
            if self._trouble is None:
                _LOGGER.warning("Couldn't get updates from Parcel: %s", err)
            self._trouble = str(err)
            if self._within_outage_grace(now):
                # A short outage: keep showing what was last known instead of turning
                # every sensor unavailable. The panel says the last check failed.
                return self.data
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        finally:
            self.storage.async_schedule_save()
        if self._trouble is not None:
            _LOGGER.info("Getting updates from Parcel again")
            self._trouble = None
        self.storage.set_rate_limited_until(None)
        snapshot = self._process(raw, now)
        # Kept only once it has been read without trouble, so a restart never starts
        # from a response that can't be.
        self.storage.remember_response(raw, now)
        if self._delivered_check_due(snapshot, now):
            await self._async_check_delivered(snapshot, now)
        self.storage.async_schedule_save()
        return snapshot

    def _within_outage_grace(self, now: datetime) -> bool:
        """Whether the last successful check is recent enough to keep showing."""
        data = self.data
        if data is None or data.fetched_at is None or self.update_interval is None:
            return False
        grace = max(OUTAGE_GRACE, self.update_interval * OUTAGE_GRACE_CHECKS)
        return now - data.fetched_at < grace

    def _pause_requests(self, retry_after: float | None) -> timedelta:
        """Parcel said "too many requests": make none for a while (within reason)."""
        asked = timedelta(seconds=min(retry_after or 0, RATE_LIMIT_MAX_PAUSE.total_seconds()))
        wait = max(RATE_LIMIT_BACKOFF, asked)
        _LOGGER.warning(
            "Parcel's rate limit was reached; pausing checks for %s minutes",
            int(wait.total_seconds() // 60),
        )
        self.storage.set_rate_limited_until(dt_util.utcnow() + wait)
        return wait

    def _keep_last_data(
        self, reason: str, retry_seconds: float, cause: Exception | None = None
    ) -> ParcelSnapshot:
        """While Parcel can't be asked, keep showing what was last known.

        Entities stay available with their last values, and the panel says checks
        are paused. Only when nothing is known yet (a first setup) is this a failure;
        Home Assistant then waits for the pause to end before trying again.
        """
        if self.data is not None:
            return self.data
        raise UpdateFailed(
            translation_domain=DOMAIN,
            translation_key=reason,
            translation_placeholders={"minutes": str(max(1, round(retry_seconds / 60)))},
            retry_after=max(1.0, retry_seconds),
        ) from cause

    def requests_paused(self) -> bool:
        """True while Parcel can't be asked: it said slow down, or this hour's checks are used."""
        now = dt_util.utcnow()
        return (
            self.storage.rate_limited_until(now) is not None
            or self.storage.reads_in_last_hour(now) >= READS_PER_HOUR
        )

    @property
    def last_error(self) -> str | None:
        """Why the latest check failed, if it did (also while old data is still shown)."""
        if self._trouble:
            return self._trouble
        if not self.last_update_success and self.last_exception is not None:
            return str(self.last_exception) or "Couldn't check Parcel"
        return None

    async def async_restore_from_cache(self, *, allow_stale: bool = False) -> bool:
        """Reuse the last saved response instead of spending a check.

        After a restart this uses a recent response. With allow_stale, any saved
        response is used, so a rate limit at startup doesn't take the integration
        down; the "updated" time shows how old it is.
        """
        cached = self.storage.cached_response()
        if cached is None or self.update_interval is None:
            return False
        fetched_at, raw = cached
        if not allow_stale and dt_util.utcnow() - fetched_at >= self.update_interval:
            return False
        self.async_set_updated_data(self._process(raw, fetched_at))
        return True

    def _adopt_records(self, listings: list[Delivery], listed: set[str]) -> None:
        """Give a newly keyed package what is remembered for it under another key.

        A key changes when Parcel writes the number differently, or when an Amazon
        shipment gains or loses its shipment ID (older versions keyed shipments by order
        number alone). The other key must name the same carrier and number and
        be missing from this reply. For Amazon, whose shipments share the order number,
        the name must match too, so one shipment never takes over another's history.
        When two listings could take the same record, the last listed does: older
        versions showed that one.
        """
        known = self.storage.known
        icons = self.storage.icons
        for delivery in reversed(listings):
            if delivery.key in known:
                continue
            shipment = by_shipment(delivery.carrier_code)
            others = [
                key
                for key, record in known.items()
                if key not in listed
                and same_package(key, delivery.carrier_code, delivery.tracking_number)
                and (
                    not shipment
                    or (
                        record["description"] == delivery.description
                        and not _other_shipment(key, delivery.key)
                    )
                )
            ]
            if len(others) != 1:
                continue
            old = others[0]
            known[delivery.key] = known.pop(old)
            if old in icons and delivery.key not in icons:
                icons[delivery.key] = icons.pop(old)
            self.storage.unlisted.pop(old, None)
            # Parcel lists it again, so the saved listing under the old key isn't shown.
            self.storage.delivered.pop(old, None)

    def _deletion_for(self, delivery: Delivery) -> str | None:
        """The delete marker hiding this package, if there is one.

        A marker saved under another spelling of the same number counts too, except
        for Amazon, where a marker is for one shipment only.
        """
        deleted = self.storage.deleted
        if delivery.key in deleted:
            return delivery.key
        if by_shipment(delivery.carrier_code):
            return None
        return next(
            (
                key
                for key in deleted
                if same_package(key, delivery.carrier_code, delivery.tracking_number)
            ),
            None,
        )

    def _keep_unlisted(
        self,
        present: set[str],
        before: Mapping[str, Delivery],
        deliveries: dict[str, Delivery],
        fetched_at: datetime,
    ) -> set[str]:
        """Remembered packages missing from this reply that aren't taken as gone yet.

        Parcel sometimes leaves packages out of a reply, even all of them. Taking that
        as final would announce them removed and then new, and lose their icons,
        history and delete markers. So a package counts as gone only once it has been
        missing for UNLISTED_GRACE; until then it is shown as it was last seen. Delete
        markers wait just as long before they go.
        """
        known = self.storage.known
        deleted = self.storage.deleted
        unlisted = self.storage.unlisted
        for key in [key for key in unlisted if key in present]:
            del unlisted[key]
        kept: set[str] = set()
        for key in [*known, *deleted]:
            if key in present:
                continue
            since = dt_util.parse_datetime(unlisted.setdefault(key, fetched_at.isoformat()))
            if since is not None and fetched_at - since < UNLISTED_GRACE:
                if key in known:
                    kept.add(key)
                    if key in before and key not in deleted:
                        deliveries[key] = before[key]
            elif key in deleted:
                del deleted[key]
        return kept

    def _note_duplicate(self, delivery: Delivery) -> None:
        """Parcel listed a package twice: keep the first listing, and say so once."""
        if delivery.key in self._duplicates:
            return
        self._duplicates.add(delivery.key)
        _LOGGER.warning(
            "Parcel lists one %s package twice; showing its first listing",
            self.carriers.name(delivery.carrier_code),
        )

    def _keep_delivered(
        self,
        listings: Mapping[str, Delivery],
        raw_listings: Mapping[str, dict[str, Any]],
        listed: set[str],
        deliveries: dict[str, Delivery],
        tz: tzinfo,
    ) -> set[str]:
        """Delivered packages Parcel's API no longer lists, shown as it last listed them.

        Parcel's API stops listing a package about a day after it's delivered, while
        Parcel keeps it until it's deleted, as its apps show. Only the web app's list
        can tell which are still there, so without a web sign-in none are kept (and
        dropping them then announces nothing: they weren't deleted). Returns the keys
        of the packages added to deliveries from what was saved.
        """
        saved = self.storage.delivered
        if self.web_client is None:
            for key in [key for key in saved if key not in listed]:
                deliveries.pop(key, None)
                self.storage.known.pop(key, None)
                self.storage.icons.pop(key, None)
                self.storage.unlisted.pop(key, None)
            saved.clear()
            self._missing_from_web.clear()
            return set()
        for key, delivery in listings.items():
            # One hidden by a delete marker isn't saved, so it can't come back later.
            if delivery.status_code == DELIVERED and key in deliveries:
                saved[key] = raw_listings[key]
            else:
                saved.pop(key, None)
        kept: set[str] = set()
        for key, listing in list(saved.items()):
            if key in listed:
                continue
            restored: Delivery | None
            try:
                restored = Delivery.from_api(listing, tz)
            except (KeyError, TypeError, ValueError, OverflowError):
                restored = None
            if (
                restored is None
                or restored.key != key
                or self._deletion_for(restored) is not None
                # Listed again under another spelling of the number.
                or (
                    not by_shipment(restored.carrier_code)
                    and any(
                        same_package(key, other.carrier_code, other.tracking_number)
                        for other in listings.values()
                    )
                )
            ):
                del saved[key]
                continue
            deliveries[key] = restored
            kept.add(key)
        return kept

    def _delivered_check_due(self, snapshot: ParcelSnapshot, now: datetime) -> bool:
        """Whether to read the web app's list now, to see which kept packages are still there.

        Hourly; sooner to confirm a package the last read left out; and right away when
        Parcel's API has just stopped listing one, since that also happens when it's
        deleted in the Parcel app.
        """
        if self.web_client is None or not snapshot.kept:
            return False
        checked = self.storage.delivered_checked_at
        if checked is None or now - checked >= DELIVERED_CHECK_INTERVAL:
            return True
        if any(now - since >= UNLISTED_GRACE for since in self._missing_from_web.values()):
            return True
        unlisted = self.storage.unlisted
        return any(
            (since := dt_util.parse_datetime(unlisted.get(key) or "")) is not None
            and since > checked
            for key in snapshot.kept
        )

    async def _async_check_delivered(self, snapshot: ParcelSnapshot, now: datetime) -> None:
        """Read the web app's list, and let go of kept packages deleted from Parcel.

        A package goes once two reads at least UNLISTED_GRACE apart both leave it out,
        so one incomplete reply loses nothing. A list without the packages Parcel's
        API says are on their way isn't this account's whole list, and changes nothing.
        """
        web = self.web_client
        if web is None:
            return
        self.storage.set_delivered_checked_at(now)
        try:
            items = await web.async_list_deliveries()
        except ParcelWebAuthError:
            self.web_sign_in.async_mark_expired()
            return
        except ParcelError as err:
            _LOGGER.debug("Couldn't see which delivered packages Parcel still has: %s", err)
            return
        self.web_sign_in.async_mark_working()
        active = {
            normalize_number(delivery.tracking_number)
            for delivery in snapshot.deliveries.values()
            if delivery.is_active
        }
        if active and not lists_any(items, active):
            _LOGGER.debug("Parcel's web list left out the packages on their way; ignoring it")
            return
        missing = self._missing_from_web
        for key in [key for key in missing if key not in snapshot.kept]:
            del missing[key]
        gone: list[str] = []
        for key in sorted(snapshot.kept):
            delivery = snapshot.deliveries[key]
            if still_listed(
                items,
                delivery.tracking_number,
                delivery.carrier_code,
                extra=delivery.extra_information,
            ):
                missing.pop(key, None)
            elif now - missing.setdefault(key, now) >= UNLISTED_GRACE:
                gone.append(key)
        if gone:
            self._forget_kept(snapshot, gone)

    def _forget_kept(self, snapshot: ParcelSnapshot, keys: list[str]) -> None:
        """Let go of kept packages that were deleted from Parcel, and announce it."""
        events: list[dict[str, Any]] = []
        for key in keys:
            self._missing_from_web.pop(key, None)
            self.storage.delivered.pop(key, None)
            self.storage.icons.pop(key, None)
            self.storage.unlisted.pop(key, None)
            snapshot.kept.discard(key)
            delivery = snapshot.deliveries.pop(key)
            remembered = self.storage.known.pop(key, None)
            record: Mapping[str, Any] = remembered or {
                "tracking_number": delivery.tracking_number,
                "carrier_code": delivery.carrier_code,
                "description": delivery.description,
                "status": delivery.status_code,
            }
            events.append(self._event_data(removal(key, record, REASON_DELETED)))
        self.storage.async_schedule_save()
        # Fire once the snapshot is current, as for the changes a check notices.
        self.hass.loop.call_soon(self._emit_all, events)

    def _process(self, raw: list[dict[str, Any]], fetched_at: datetime) -> ParcelSnapshot:
        tz = dt_util.get_default_time_zone()
        self.storage.prune(fetched_at)
        before = self.data.deliveries if self.data else {}
        listings: dict[str, Delivery] = {}
        raw_listings: dict[str, dict[str, Any]] = {}
        unreadable: set[str] = set()
        for listing in raw:
            try:
                delivery = Delivery.from_api(listing, tz)
            except (KeyError, TypeError, ValueError, OverflowError) as err:
                # One odd package mustn't take the rest down with it. If it can still
                # be told which package it is, that one stays as it was last seen.
                _LOGGER.debug("Skipping a delivery in an unexpected format: %r", err)
                if key := listing_key(listing):
                    unreadable.add(key)
                continue
            if delivery.key in listings:
                self._note_duplicate(delivery)
                continue
            listings[delivery.key] = delivery
            raw_listings[delivery.key] = listing
        listed = listings.keys() | unreadable
        self._adopt_records(list(listings.values()), listed)

        deliveries: dict[str, Delivery] = {}
        markers: set[str] = set()
        for key, delivery in listings.items():
            if marker := self._deletion_for(delivery):
                markers.add(marker)
            else:
                deliveries[key] = delivery
        for key in unreadable - listings.keys():
            if key in before and key not in self.storage.deleted:
                deliveries[key] = before[key]
        # A delete marker is only needed while Parcel's cached list still shows the
        # package. Once it's gone the marker goes too, so the same package shows up
        # again if it's added again later.
        waiting = self._keep_unlisted(listed | markers, before, deliveries, fetched_at)
        kept = self._keep_delivered(listings, raw_listings, listed, deliveries, tz)

        # Packages added from Home Assistant wait in "pending" until Parcel lists them.
        # Parcel stores a number of its own for placeholders, so for those a newly
        # listed package with the same carrier and name also counts as a match.
        known = self.storage.known
        unclaimed = [key for key in deliveries if key not in known]
        icons = self.storage.icons
        stored_pending = self.storage.pending
        pending: dict[str, PendingAdd] = {}
        for key, item in list(stored_pending.items()):
            match = key if key in deliveries else match_pending(item, deliveries, unclaimed)
            if match is not None:
                del stored_pending[key]
                if match in unclaimed:
                    unclaimed.remove(match)
                if match != key and key in icons:
                    icons.setdefault(match, icons.pop(key))
                continue
            if restored := PendingAdd.from_store(key, item):
                pending[key] = restored
        # Icon choices go when their package does.
        for key in [
            key
            for key in icons
            if key not in deliveries and key not in stored_pending and key not in waiting
        ]:
            del icons[key]

        changes = detect_changes(
            known, deliveries, fetched_at, announce=self.storage.initialized, keep=waiting
        )
        self.storage.mark_initialized()
        unlisted = self.storage.unlisted
        for key in [
            key for key in unlisted if key not in known and key not in self.storage.deleted
        ]:
            del unlisted[key]
        if changes:
            # Fire after the new data is in place, so automations see current counts.
            events = [self._event_data(change) for change in changes]
            self.hass.loop.call_soon(self._emit_all, events)
        return ParcelSnapshot(
            deliveries=deliveries, pending=pending, fetched_at=fetched_at, kept=kept
        )

    # Reading -----------------------------------------------------------------

    def delivered_at(self, delivery: Delivery) -> datetime | None:
        """When a delivered package arrived, if known."""
        if delivery.is_active:
            return None
        record = self.storage.known.get(delivery.key)
        stamp = record.get("delivered_at") if record else None
        if stamp and (parsed := dt_util.parse_datetime(stamp)):
            return parsed
        latest = delivery.latest_event
        return latest.when if latest and latest.when else None

    def icon_for(self, key: str, description: str) -> str:
        """The icon a person chose, or one guessed from the name."""
        return self.storage.icons.get(key) or guess_icon(description)

    def summary(self) -> Summary:
        """Counts and lists for the summary sensors, worked out once per change and day."""
        now = dt_util.now()
        today = now.date()
        if self._summary is None or self._summary[0] != today:
            deliveries = self.data.deliveries.values() if self.data else ()
            self._summary = (today, build_summary(deliveries, self.delivered_at, now))
        return self._summary[1]

    def wants_package_sensor(self, delivery: Delivery) -> bool:
        """Per-package sensors go away two days after delivery.

        When the delivery time isn't known, two days after the package was first seen,
        so a delivered package kept on show doesn't keep its sensor for good.
        """
        if delivery.is_active:
            return True
        when = self.delivered_at(delivery)
        if when is None and (record := self.storage.known.get(delivery.key)):
            when = dt_util.parse_datetime(record["first_seen"])
        return when is None or dt_util.utcnow() - when < DELIVERED_SENSOR_RETENTION

    def active_numbers(self, *, besides: str | None = None) -> set[str]:
        """Normalized numbers of the listed packages still on their way (optionally but one)."""
        snapshot = self.data or ParcelSnapshot()
        return {
            normalize_number(delivery.tracking_number)
            for key, delivery in snapshot.deliveries.items()
            if delivery.is_active and key != besides
        }

    def find_keys(self, tracking_number: str, carrier_code: str | None = None) -> list[str]:
        """Keys of tracked packages (listed, or just added) with this tracking number.

        Spaces, dashes and letter case in the number don't matter. One shipment of an
        Amazon order can be named as "<order number>@<shipment ID>", as in its key.
        """
        snapshot = self.data or ParcelSnapshot()
        wanted = normalize_number(tracking_number)
        tracked: list[tuple[str, Delivery | PendingAdd]] = [
            *snapshot.deliveries.items(),
            *snapshot.pending.items(),
        ]
        return [
            key
            for key, item in tracked
            if wanted
            in (normalize_number(item.tracking_number), normalize_number(split_key(key)[1]))
            and (carrier_code is None or item.carrier_code == carrier_code)
        ]

    def panel_state(self) -> dict[str, Any]:
        """What the sidebar panel needs for this account."""
        now = dt_util.utcnow()
        snapshot = self.data or ParcelSnapshot()
        known = self.storage.known
        icons = self.storage.icons
        deliveries = []
        for delivery in snapshot.deliveries.values():
            item = delivery.as_dict()
            when = self.delivered_at(delivery)
            record = known.get(delivery.key)
            item.update(
                {
                    "carrier_name": self.carriers.name(delivery.carrier_code),
                    "carrier_short": self.carriers.short_name(delivery.carrier_code),
                    "icon": self.icon_for(delivery.key, delivery.description),
                    "icon_source": "user" if delivery.key in icons else "name",
                    "delivered_at": when.isoformat() if when else None,
                    "first_seen": record.get("first_seen") if record else None,
                }
            )
            deliveries.append(item)
        pending = [
            {
                "key": item.key,
                "tracking_number": item.tracking_number,
                "carrier_code": item.carrier_code,
                "carrier_name": self.carriers.name(item.carrier_code),
                "carrier_short": self.carriers.short_name(item.carrier_code),
                "description": item.description,
                "added_at": item.added_at.isoformat(),
                "icon": self.icon_for(item.key, item.description),
                "icon_source": "user" if item.key in icons else "name",
            }
            for item in snapshot.pending.values()
        ]
        paused_until = self.storage.rate_limited_until(now)
        return {
            "entry_id": self.config_entry.entry_id,
            "title": self.config_entry.title,
            "can_delete": self.web_client is not None,
            "adds_left": max(0, ADDS_PER_DAY - self.storage.adds_in_last_day(now)),
            "adds_limit": ADDS_PER_DAY,
            "checks_left": max(0, READS_PER_HOUR - self.storage.reads_in_last_hour(now)),
            "interval_minutes": int(self.update_interval.total_seconds() // 60)
            if self.update_interval
            else None,
            "updated_at": snapshot.fetched_at.isoformat() if snapshot.fetched_at else None,
            "paused_until": paused_until.isoformat() if paused_until else None,
            "last_error": self.last_error,
            "deliveries": deliveries,
            "pending": pending,
        }

    # Actions -----------------------------------------------------------------

    async def async_manual_refresh(self) -> None:
        """Check Parcel now, unless that would eat into the scheduled checks."""
        now = dt_util.utcnow()
        if (
            self.data
            and self.data.fetched_at
            and now - self.data.fetched_at < MANUAL_REFRESH_MIN_GAP
        ):
            return
        if until := self.storage.rate_limited_until(now):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rate_limit_pause",
                translation_placeholders={
                    "minutes": str(max(1, int((until - now).total_seconds() // 60) + 1))
                },
            )
        if self.storage.reads_in_last_hour(now) >= READS_PER_HOUR - MANUAL_REFRESH_RESERVE:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="refresh_limit",
                translation_placeholders={"minutes": str(self.storage.minutes_until_read(now))},
            )
        await self.async_refresh()
        if error := self.last_error:
            # Also when the check failed but the last known packages are still shown.
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": error},
            )

    async def async_add_package(
        self,
        *,
        tracking_number: str,
        description: str,
        carrier_code: str | None = None,
        extra: str | None = None,
        postcode: str | None = None,
        email: str | None = None,
        send_push_confirmation: bool = False,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Add a package to Parcel. Parcel allows 20 adds a day, failures included.

        Some carriers need one more detail. Pass it as postcode or email, or as extra
        to have it sent as whichever the carrier asks for.
        """
        number = re.sub(r"\s+", "", tracking_number or "")
        name = (description or "").strip()
        if not number:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="tracking_number_required"
            )
        if not name:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="description_required"
            )
        if icon is not None and not ICON_FORMAT.match(icon):
            icon = None
        carriers = await self.carriers.async_ensure_loaded()
        carrier = (carrier_code or "").strip().lower()
        if not carrier:
            matches = detect_carriers(number, carriers or None)
            if not matches:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="carrier_required"
                )
            carrier = matches[0]
        if carriers and carrier not in carriers:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_carrier",
                translation_placeholders={"carrier": carrier},
            )
        claim = (carrier, normalize_number(number))
        if self.find_keys(number, carrier) or claim in self._adding:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="already_tracking",
                translation_placeholders={"number": number},
            )
        # The carrier decides whether "extra" is an email or a postcode.
        extra_kind = self.carriers.extra(carrier)
        send_postcode = _text(postcode)
        send_email = _text(email)
        if extra_kind == EXTRA_EMAIL:
            send_email = send_email or _text(extra)
        elif extra_kind:
            send_postcode = send_postcode or _text(extra)
        if extra_kind and not (send_email if extra_kind == EXTRA_EMAIL else send_postcode):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="extra_required",
                translation_placeholders={"carrier": self.carriers.name(carrier)},
            )
        now = dt_util.utcnow()
        if self.storage.adds_in_last_day(now) >= ADDS_PER_DAY:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="add_limit")
        language = (self.hass.config.language or "en").split("-")[0].lower() or "en"
        self.storage.record_add(now)
        self.storage.async_schedule_save()
        self._adding.add(claim)
        try:
            await self.client.async_add_delivery(
                tracking_number=number,
                carrier_code=carrier,
                description=name,
                language=language,
                send_push_confirmation=send_push_confirmation,
                postcode=send_postcode,
                email=send_email,
            )
        except ParcelAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_api_key"
            ) from err
        except ParcelRateLimitError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="add_limit"
            ) from err
        except ParcelRequestError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="add_rejected",
                translation_placeholders={"error": str(err)},
            ) from err
        except ParcelError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="add_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        finally:
            self._adding.discard(claim)

        key = package_key(carrier, number)
        added = PendingAdd(key, number, carrier, name, now)
        self.storage.pending[key] = added.to_store()
        # If this package was deleted here earlier, it's wanted again.
        deleted = self.storage.deleted
        for old in [old for old in deleted if same_package(old, carrier, number)]:
            del deleted[old]
        if icon:
            self.storage.icons[key] = icon
        self.storage.async_schedule_save()
        if self.data is not None:
            self.data.pending[key] = added
        self.async_update_listeners()
        self._schedule_follow_up()
        return {"key": key, "carrier": carrier, "carrier_name": self.carriers.name(carrier)}

    def _schedule_follow_up(self) -> None:
        """Check again a little after an add, so the new package shows up sooner."""
        if self._follow_up_unsub:
            self._follow_up_unsub()

        async def _follow_up(_now: datetime) -> None:
            self._follow_up_unsub = None
            if (
                self.storage.reads_in_last_hour(dt_util.utcnow())
                < READS_PER_HOUR - MANUAL_REFRESH_RESERVE
            ):
                await self.async_request_refresh()

        self._follow_up_unsub = async_call_later(self.hass, FOLLOW_UP_REFRESH_SECONDS, _follow_up)

    async def async_delete_package(self, key: str) -> None:
        """Delete a package from Parcel (all devices) using the web sign-in."""
        web = self.web_client
        if web is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="delete_needs_sign_in"
            )
        snapshot = self.data or ParcelSnapshot()
        delivery = snapshot.deliveries.get(key)
        target = delivery or snapshot.pending.get(key)
        if target is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="package_not_found"
            )
        number = target.tracking_number
        carrier = target.carrier_code
        name = target.description
        try:
            # Delete exactly what Parcel stored, then confirm it's gone: Parcel reports
            # success even when nothing matched (like the web app, re-read the list).
            # A package is found by its number; only a placeholder Parcel hasn't listed
            # yet may be found by its name, because Parcel numbers placeholders itself.
            items = await web.async_list_deliveries()
            stored = find_stored(
                items,
                number,
                carrier,
                extra=delivery.extra_information if delivery else None,
                unlisted_name=name if delivery is None else None,
                listed_numbers={
                    normalize_number(item.tracking_number) for item in snapshot.deliveries.values()
                },
            )
            if stored is None and lists_number(items, number, carrier):
                # Parcel has the number, but not so that it says which package this is
                # (say, an Amazon order shipped in parts): never take it as deleted.
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="delete_ambiguous"
                )
            if stored is None:
                self._check_not_found(items, key, listed=delivery is not None)
            else:
                await web.async_delete_delivery(stored[0], stored[1])
                if find_stored(await web.async_list_deliveries(), stored[0], stored[1]):
                    raise HomeAssistantError(
                        translation_domain=DOMAIN, translation_key="delete_not_confirmed"
                    )
        except ParcelWebAuthError as err:
            self.web_sign_in.async_mark_expired()
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="web_sign_in_expired"
            ) from err
        except ParcelError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="delete_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        self.web_sign_in.async_mark_working()

        self.storage.mark_deleted(key, dt_util.utcnow())
        self.storage.pending.pop(key, None)
        self.storage.icons.pop(key, None)
        self.storage.delivered.pop(key, None)
        self._missing_from_web.pop(key, None)
        remembered = self.storage.known.pop(key, None)
        record: Mapping[str, Any] = remembered or {
            "tracking_number": number,
            "carrier_code": carrier,
            "description": name,
            "status": delivery.status_code if delivery else NOT_FOUND,
        }
        # A check may have finished while Parcel's web app was answering, replacing
        # the snapshot read above: take the package out of what is current now.
        if (current := self.data) is not None:
            current.deliveries.pop(key, None)
            current.pending.pop(key, None)
            current.kept.discard(key)
        self.storage.async_schedule_save()
        self.async_update_listeners()
        self._emit(self._event_data(removal(key, record, REASON_DELETED)))

    def _check_not_found(self, items: list[dict[str, Any]], key: str, *, listed: bool) -> None:
        """A package missing from the web app's list: say why, unless it was deleted elsewhere.

        Only a package Parcel's API still lists can have been deleted elsewhere a moment
        ago, and only this account's own list can show that. Anything else is refused,
        so nothing is hidden here that is still in Parcel.
        """
        others = self.active_numbers(besides=key)
        if others and not lists_any(items, others):
            # None of the account's other packages on their way are in it either.
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="web_sign_in_other_account"
            )
        if not listed:
            # Added from Home Assistant, and Parcel hasn't stored it yet.
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="delete_not_added_yet"
            )

    @callback
    def async_set_icon(self, key: str, icon: str | None) -> None:
        """Remember a person's icon choice (None goes back to guessing)."""
        snapshot = self.data or ParcelSnapshot()
        if key not in snapshot.deliveries and key not in snapshot.pending:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="package_not_found"
            )
        if icon and ICON_FORMAT.match(icon):
            self.storage.icons[key] = icon
        else:
            self.storage.icons.pop(key, None)
        self.storage.async_schedule_save()
        self.async_update_listeners()

    async def async_shutdown(self) -> None:
        """Stop timers and save before unloading."""
        await super().async_shutdown()
        if self._follow_up_unsub:
            self._follow_up_unsub()
            self._follow_up_unsub = None
        self.web_sign_in.async_stop()
        await self.storage.async_save_now()
