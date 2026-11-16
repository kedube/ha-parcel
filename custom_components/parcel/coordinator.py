"""Polls Parcel, notices changes, and runs add and delete for one account."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later, async_track_time_interval
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
from .const import (
    ADDS_PER_DAY,
    CONF_ACCOUNT_TOKEN_SET_AT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_MINUTES,
    DELIVERED_SENSOR_RETENTION,
    DOMAIN,
    EVENT_ADDED,
    EVENT_DELIVERED,
    EVENT_IN_TRANSIT,
    EVENT_LABEL_CREATED,
    EVENT_NEEDS_ATTENTION,
    EVENT_OUT_FOR_DELIVERY,
    EVENT_PACKAGE_UPDATE,
    EVENT_READY_FOR_PICKUP,
    EVENT_REMOVED,
    EVENT_UPDATE,
    FOLLOW_UP_REFRESH_SECONDS,
    MANUAL_REFRESH_MIN_GAP,
    MANUAL_REFRESH_RESERVE,
    RATE_LIMIT_BACKOFF,
    READS_PER_HOUR,
    WEB_SIGN_IN_CHECK_INTERVAL,
    WEB_SIGN_IN_DOCS_URL,
    WEB_SIGN_IN_FIRST_CHECK,
    WEB_TOKEN_LIFETIME,
    WEB_TOKEN_WARN_AHEAD,
)
from .models import (
    DELIVERED,
    EXCEPTION,
    FAILED_ATTEMPT,
    OUT_FOR_DELIVERY,
    READY_FOR_PICKUP,
    STALLED,
    STATUS_SLUGS,
    Delivery,
    TrackingEvent,
    detect_carriers,
    guess_icon,
    normalize_number,
)
from .storage import ParcelStorage

_LOGGER = logging.getLogger(__name__)

type ParcelConfigEntry = ConfigEntry[ParcelCoordinator]

STATUS_EVENTS: dict[int, str] = {
    0: EVENT_DELIVERED,
    1: EVENT_NEEDS_ATTENTION,
    2: EVENT_IN_TRANSIT,
    3: EVENT_READY_FOR_PICKUP,
    4: EVENT_OUT_FOR_DELIVERY,
    5: EVENT_UPDATE,
    6: EVENT_NEEDS_ATTENTION,
    7: EVENT_NEEDS_ATTENTION,
    8: EVENT_LABEL_CREATED,
}
ICON_FORMAT = re.compile(r"^mdi:[a-z0-9-]+$")

type EventListener = Callable[[str, dict[str, Any]], None]


@dataclass(slots=True)
class PendingAdd:
    """A package added from Home Assistant that Parcel hasn't listed yet."""

    key: str
    tracking_number: str
    carrier_code: str
    description: str
    added_at: datetime

    @classmethod
    def from_store(cls, key: str, item: dict[str, Any]) -> PendingAdd | None:
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

    def to_store(self) -> dict[str, Any]:
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


@dataclass(slots=True)
class Summary:
    """The high-level picture used by the summary sensors."""

    out_for_delivery: list[Delivery]
    arriving_today: list[Delivery]
    needs_attention: list[Delivery]
    ready_for_pickup: list[Delivery]
    on_the_way: list[Delivery]
    delivered_today: list[Delivery]
    next_delivery: Delivery | None
    next_delivery_at: datetime | None


def event_message(etype: str, delivery: Delivery, carrier: str) -> str:
    """A sentence ready to use in a notification."""
    name = delivery.description
    latest = delivery.latest_event
    if etype == EVENT_ADDED:
        return f"Now tracking {name}"
    if etype == EVENT_LABEL_CREATED:
        return f"{name} has a shipping label. {carrier} doesn't have it yet"
    if etype == EVENT_IN_TRANSIT:
        return f"{name} is on the way"
    if etype == EVENT_OUT_FOR_DELIVERY:
        return f"{name} is out for delivery"
    if etype == EVENT_READY_FOR_PICKUP:
        where = f" at {latest.location}" if latest and latest.location else ""
        return f"{name} is ready for pickup{where}"
    if etype == EVENT_DELIVERED:
        return f"{name} was delivered"
    if etype == EVENT_NEEDS_ATTENTION:
        if delivery.status_code == FAILED_ATTEMPT:
            return f"{carrier} missed the delivery of {name}"
        if delivery.status_code == EXCEPTION:
            detail = f": {latest.text}" if latest else ""
            return f"{name} has a delivery problem{detail}"
        if delivery.status_code == STALLED:
            return f"{name} hasn't had an update in a while"
    if etype == EVENT_REMOVED:
        return f"{name} is no longer tracked"
    if latest:
        return f"{name}: {latest.text}"
    return f"{name} has an update"


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
        self.web_client: ParcelWebClient | None = None
        self.device_id: str | None = None
        self._event_listeners: list[EventListener] = []
        self._follow_up_unsub: CALLBACK_TYPE | None = None
        self._web_check_unsub: CALLBACK_TYPE | None = None
        self._web_first_check_unsub: CALLBACK_TYPE | None = None
        self._issue_expired = f"web_sign_in_{entry.entry_id}"
        self._issue_expiring = f"web_sign_in_expiring_{entry.entry_id}"

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
    def _emit(self, etype: str, data: dict[str, Any]) -> None:
        self.hass.bus.async_fire(EVENT_PACKAGE_UPDATE, data)
        for listener in list(self._event_listeners):
            listener(etype, data)

    @callback
    def _emit_all(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        for etype, data in events:
            self._emit(etype, data)

    def _event_data(self, etype: str, delivery: Delivery, previous: int | None) -> dict[str, Any]:
        latest = delivery.latest_event
        carrier = self.carriers.name(delivery.carrier_code)
        data: dict[str, Any] = {
            "entry_id": self.config_entry.entry_id,
            "device_id": self.device_id,
            "type": etype,
            "key": delivery.key,
            "description": delivery.description,
            "tracking_number": delivery.tracking_number,
            "carrier_code": delivery.carrier_code,
            "carrier": carrier,
            "status": delivery.status,
            "previous_status": STATUS_SLUGS.get(previous) if previous is not None else None,
            "event": latest.text if latest else None,
            "location": latest.location if latest else None,
            "message": event_message(etype, delivery, carrier),
        }
        if etype == EVENT_NEEDS_ATTENTION:
            data["reason"] = delivery.status
        return data

    def _removed_data(self, key: str, known: dict[str, Any], reason: str) -> dict[str, Any]:
        stub = Delivery(
            key=key,
            tracking_number=known.get("tracking_number", ""),
            carrier_code=known.get("carrier_code", ""),
            description=known.get("description") or known.get("tracking_number", ""),
            status_code=int(known.get("status", 5)),
            events=(),
            extra_information=None,
            eta_start=None,
            eta_end=None,
            eta_date=None,
        )
        data = self._event_data(EVENT_REMOVED, stub, stub.status_code)
        data["reason"] = reason
        return data

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
            # Write now, not after the usual delay, so a restart or setup retry sees it.
            await self.storage.async_save_now()
            return self._keep_last_data("rate_limited", wait.total_seconds(), err)
        except ParcelError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        finally:
            self.storage.async_schedule_save()
        self.storage.set_rate_limited_until(None)
        self.storage.data["cache"] = {"fetched_at": now.isoformat(), "deliveries": raw}
        snapshot = self._process(raw, now)
        self.storage.async_schedule_save()
        return snapshot

    def _pause_requests(self, retry_after: float | None) -> timedelta:
        """Parcel said "too many requests": make none for a while."""
        wait = max(RATE_LIMIT_BACKOFF, timedelta(seconds=retry_after or 0))
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
            retry_after=max(1.0, retry_seconds),
        ) from cause

    def requests_paused(self) -> bool:
        """True while Parcel can't be asked: it said slow down, or this hour's checks are used."""
        now = dt_util.utcnow()
        return (
            self.storage.rate_limited_until(now) is not None
            or self.storage.reads_in_last_hour(now) >= READS_PER_HOUR
        )

    async def async_restore_from_cache(self, *, allow_stale: bool = False) -> bool:
        """Reuse the last saved response instead of spending a check.

        After a restart this uses a recent response. With allow_stale, any saved
        response is used, so a rate limit at startup doesn't take the integration
        down; the "updated" time shows how old it is.
        """
        cache = self.storage.data.get("cache") or {}
        fetched_at = dt_util.parse_datetime(cache.get("fetched_at") or "")
        raw = cache.get("deliveries")
        if not fetched_at or not isinstance(raw, list) or self.update_interval is None:
            return False
        if not allow_stale and dt_util.utcnow() - fetched_at >= self.update_interval:
            return False
        self.async_set_updated_data(self._process(raw, fetched_at))
        return True

    def _process(self, raw: list[dict[str, Any]], fetched_at: datetime) -> ParcelSnapshot:
        tz = dt_util.get_default_time_zone()
        self.storage.prune(fetched_at)
        deleted = self.storage.data["deleted"]
        deliveries: dict[str, Delivery] = {}
        for item in raw:
            try:
                delivery = Delivery.from_api(item, tz)
            except (KeyError, TypeError, ValueError) as err:
                _LOGGER.debug("Skipping a delivery in an unexpected format: %s", err)
                continue
            if delivery.key not in deleted:
                deliveries[delivery.key] = delivery

        # Packages added from Home Assistant wait in "pending" until Parcel lists them.
        # Parcel may store a different number (it generates one for placeholders), so a
        # newly listed package with the same carrier and name also counts as a match.
        known = self.storage.data["known"]
        unclaimed = [key for key in deliveries if key not in known]
        icons = self.storage.data["icons"]
        pending: dict[str, PendingAdd] = {}
        for key, item in list(self.storage.data["pending"].items()):
            match = key if key in deliveries else _match_pending(item, deliveries, unclaimed)
            if match is not None:
                del self.storage.data["pending"][key]
                if match in unclaimed:
                    unclaimed.remove(match)
                if match != key and key in icons:
                    icons.setdefault(match, icons.pop(key))
                continue
            if restored := PendingAdd.from_store(key, item):
                pending[key] = restored

        events = self._track_changes(deliveries, fetched_at)
        if events:
            # Fire after the new data is in place, so automations see current counts.
            self.hass.loop.call_soon(self._emit_all, events)
        return ParcelSnapshot(deliveries=deliveries, pending=pending, fetched_at=fetched_at)

    def _track_changes(
        self, deliveries: dict[str, Delivery], now: datetime
    ) -> list[tuple[str, dict[str, Any]]]:
        known: dict[str, dict[str, Any]] = self.storage.data["known"]
        announce = bool(self.storage.data.get("initialized"))
        events: list[tuple[str, dict[str, Any]]] = []
        for key, delivery in deliveries.items():
            latest = delivery.latest_event
            signature = latest.signature if latest else ""
            previous = known.get(key)
            if previous is None:
                known[key] = {
                    "status": delivery.status_code,
                    "first_seen": now.isoformat(),
                    "delivered_at": _delivered_time(delivery, latest, None),
                    "event": signature,
                    "description": delivery.description,
                    "tracking_number": delivery.tracking_number,
                    "carrier_code": delivery.carrier_code,
                }
                if announce:
                    events.append((EVENT_ADDED, self._event_data(EVENT_ADDED, delivery, None)))
                continue
            old_status = previous.get("status")
            previous["description"] = delivery.description
            if old_status != delivery.status_code:
                if delivery.status_code == DELIVERED and not previous.get("delivered_at"):
                    previous["delivered_at"] = _delivered_time(delivery, latest, now)
                etype = STATUS_EVENTS.get(delivery.status_code, EVENT_UPDATE)
                events.append((etype, self._event_data(etype, delivery, old_status)))
            elif signature and signature != previous.get("event"):
                events.append((EVENT_UPDATE, self._event_data(EVENT_UPDATE, delivery, old_status)))
            previous["status"] = delivery.status_code
            previous["event"] = signature
        for key in [key for key in known if key not in deliveries]:
            gone = known.pop(key)
            if announce:
                events.append((EVENT_REMOVED, self._removed_data(key, gone, "no_longer_listed")))
        self.storage.data["initialized"] = True
        return events

    # Reading -----------------------------------------------------------------

    def delivered_at(self, delivery: Delivery) -> datetime | None:
        """When a delivered package arrived, if known."""
        if delivery.is_active:
            return None
        stamp = self.storage.data["known"].get(delivery.key, {}).get("delivered_at")
        if stamp and (parsed := dt_util.parse_datetime(stamp)):
            return parsed
        latest = delivery.latest_event
        return latest.when if latest and latest.when else None

    def icon_for(self, key: str, description: str) -> str:
        """The icon a person chose, or one guessed from the name."""
        return self.storage.data["icons"].get(key) or guess_icon(description)

    def summary(self) -> Summary:
        """Counts and lists for the summary sensors."""
        tz = dt_util.get_default_time_zone()
        today = dt_util.now(tz).date()
        far = datetime.max.replace(tzinfo=tz)
        items = sorted(
            (self.data.deliveries if self.data else {}).values(),
            key=lambda d: d.expected_sort_time(tz) or far,
        )
        active = [d for d in items if d.is_active]
        delivered_today = [
            d
            for d in items
            if not d.is_active
            and (when := self.delivered_at(d)) is not None
            and when.astimezone(tz).date() == today
        ]
        upcoming = [
            (when, d)
            for d in active
            if not d.needs_attention
            and (when := d.expected_sort_time(tz)) is not None
            and when.astimezone(tz).date() >= today
        ]
        nxt = min(upcoming, key=lambda pair: pair[0]) if upcoming else None
        return Summary(
            out_for_delivery=[d for d in active if d.status_code == OUT_FOR_DELIVERY],
            arriving_today=[
                d
                for d in active
                if not d.needs_attention
                and (d.status_code == OUT_FOR_DELIVERY or d.expected_day(tz) == today)
            ],
            needs_attention=[d for d in active if d.needs_attention],
            ready_for_pickup=[d for d in active if d.status_code == READY_FOR_PICKUP],
            on_the_way=[d for d in active if d.status_code != READY_FOR_PICKUP],
            delivered_today=delivered_today,
            next_delivery=nxt[1] if nxt else None,
            next_delivery_at=nxt[0] if nxt else None,
        )

    def wants_package_sensor(self, delivery: Delivery) -> bool:
        """Per-package sensors go away two days after delivery."""
        if delivery.is_active:
            return True
        when = self.delivered_at(delivery)
        return when is None or dt_util.utcnow() - when < DELIVERED_SENSOR_RETENTION

    def panel_state(self) -> dict[str, Any]:
        """What the sidebar panel needs for this account."""
        now = dt_util.utcnow()
        snapshot = self.data or ParcelSnapshot()
        known = self.storage.data["known"]
        icons = self.storage.data["icons"]
        deliveries = []
        for delivery in snapshot.deliveries.values():
            item = delivery.as_dict()
            when = self.delivered_at(delivery)
            item.update(
                {
                    "carrier_name": self.carriers.name(delivery.carrier_code),
                    "carrier_short": self.carriers.short_name(delivery.carrier_code),
                    "icon": self.icon_for(delivery.key, delivery.description),
                    "icon_source": "user" if delivery.key in icons else "name",
                    "delivered_at": when.isoformat() if when else None,
                    "first_seen": known.get(delivery.key, {}).get("first_seen"),
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
        error = None
        if not self.last_update_success and self.last_exception is not None:
            error = str(self.last_exception) or "Couldn't check Parcel"
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
            "last_error": error,
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
        if not self.last_update_success:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(self.last_exception or "")},
            )

    async def async_add_package(
        self,
        *,
        tracking_number: str,
        description: str,
        carrier_code: str | None = None,
        extra: str | None = None,
        send_push_confirmation: bool = False,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Add a package to Parcel. Parcel allows 20 adds a day, failures included."""
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
        key = f"{carrier}:{number}"
        snapshot = self.data or ParcelSnapshot()
        if key in snapshot.deliveries or key in snapshot.pending:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="already_tracking",
                translation_placeholders={"number": number},
            )
        extra_kind = self.carriers.extra(carrier)
        extra_value = (extra or "").strip() or None
        if extra_kind and not extra_value:
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
        try:
            await self.client.async_add_delivery(
                tracking_number=number,
                carrier_code=carrier,
                description=name,
                language=language,
                send_push_confirmation=send_push_confirmation,
                postcode=extra_value if extra_kind and extra_kind != EXTRA_EMAIL else None,
                email=extra_value if extra_kind == EXTRA_EMAIL else None,
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

        added = PendingAdd(key, number, carrier, name, now)
        self.storage.data["pending"][key] = added.to_store()
        if icon:
            self.storage.data["icons"][key] = icon
        self.storage.async_schedule_save()
        if self.data is not None:
            self.data.pending[key] = added
        self.async_update_listeners()
        self._schedule_follow_up()
        return {"key": key, "carrier": carrier, "carrier_name": self.carriers.name(carrier)}

    # Web sign-in health -----------------------------------------------------

    @callback
    def async_start_web_sign_in_checks(self) -> None:
        """Begin checking the web sign-in daily, and once shortly after startup."""
        if self.web_client is None:
            return
        self._web_check_unsub = async_track_time_interval(
            self.hass, self._async_check_web_sign_in, WEB_SIGN_IN_CHECK_INTERVAL
        )
        self._web_first_check_unsub = async_call_later(
            self.hass, WEB_SIGN_IN_FIRST_CHECK, self._async_first_web_sign_in_check
        )

    async def _async_first_web_sign_in_check(self, _now: datetime) -> None:
        """The one-off check shortly after startup."""
        self._web_first_check_unsub = None
        await self._async_check_web_sign_in()

    def _web_sign_in_remaining(self) -> timedelta | None:
        """How long until the pasted token reaches its 360-day lifetime, if known."""
        stamp = self.config_entry.options.get(CONF_ACCOUNT_TOKEN_SET_AT)
        set_at = dt_util.parse_datetime(stamp) if stamp else None
        if set_at is None:
            return None
        return (set_at + WEB_TOKEN_LIFETIME) - dt_util.utcnow()

    def _raise_web_sign_in_expired(self) -> None:
        """Ask for a new token, and drop the softer 'expiring soon' notice."""
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._issue_expired,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="web_sign_in_expired",
            translation_placeholders={"title": self.config_entry.title},
            learn_more_url=WEB_SIGN_IN_DOCS_URL,
        )
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_expiring)

    async def _async_check_web_sign_in(self, _now: datetime | None = None) -> None:
        """Daily: confirm the token still works and warn before it expires."""
        if self.web_client is None:
            return
        try:
            await self.web_client.async_validate()
        except ParcelWebAuthError:
            self._raise_web_sign_in_expired()
            return
        except ParcelError as err:
            _LOGGER.debug("Couldn't check the Parcel web sign-in; will retry: %s", err)
            return
        # The token works. Clear any expiry warning, and raise a gentle heads-up
        # when it's within two weeks of Parcel's 360-day limit.
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_expired)
        remaining = self._web_sign_in_remaining()
        if remaining is not None and remaining <= WEB_TOKEN_WARN_AHEAD:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_expiring,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="web_sign_in_expiring",
                translation_placeholders={
                    "title": self.config_entry.title,
                    "days": str(max(0, remaining.days)),
                },
                learn_more_url=WEB_SIGN_IN_DOCS_URL,
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_expiring)

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
        if self.web_client is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="delete_needs_sign_in"
            )
        snapshot = self.data or ParcelSnapshot()
        delivery = snapshot.deliveries.get(key)
        pending = snapshot.pending.get(key)
        if delivery is None and pending is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="package_not_found"
            )
        number = delivery.tracking_number if delivery else pending.tracking_number  # type: ignore[union-attr]
        carrier = delivery.carrier_code if delivery else pending.carrier_code  # type: ignore[union-attr]
        name = delivery.description if delivery else pending.description  # type: ignore[union-attr]
        try:
            # Delete exactly what Parcel stored, then confirm it's gone: Parcel reports
            # success even when nothing matched (like the web app, re-read the list).
            stored = _find_stored(
                await self.web_client.async_list_deliveries(), number, carrier, name
            )
            if stored is not None:
                await self.web_client.async_delete_delivery(stored[0], stored[1])
                if _find_stored(
                    await self.web_client.async_list_deliveries(), stored[0], stored[1], None
                ):
                    raise HomeAssistantError(
                        translation_domain=DOMAIN, translation_key="delete_not_confirmed"
                    )
        except ParcelWebAuthError as err:
            self._raise_web_sign_in_expired()
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="web_sign_in_expired"
            ) from err
        except ParcelError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="delete_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        # The sign-in just worked, so clear any warnings about it.
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_expired)

        now = dt_util.utcnow()
        store = self.storage.data
        store["deleted"][key] = now.isoformat()
        store["pending"].pop(key, None)
        store["icons"].pop(key, None)
        known = store["known"].pop(key, None) or {
            "tracking_number": number,
            "carrier_code": carrier,
            "description": delivery.description if delivery else pending.description,  # type: ignore[union-attr]
            "status": delivery.status_code if delivery else 5,
        }
        snapshot.deliveries.pop(key, None)
        snapshot.pending.pop(key, None)
        self.storage.async_schedule_save()
        self.async_update_listeners()
        self._emit(EVENT_REMOVED, self._removed_data(key, known, "deleted"))

    @callback
    def async_set_icon(self, key: str, icon: str | None) -> None:
        """Remember a person's icon choice (None goes back to guessing)."""
        icons = self.storage.data["icons"]
        if icon and ICON_FORMAT.match(icon):
            icons[key] = icon
        else:
            icons.pop(key, None)
        self.storage.async_schedule_save()
        self.async_update_listeners()

    async def async_shutdown(self) -> None:
        """Stop timers and save before unloading."""
        await super().async_shutdown()
        for unsub in ("_follow_up_unsub", "_web_check_unsub", "_web_first_check_unsub"):
            if cancel := getattr(self, unsub):
                cancel()
                setattr(self, unsub, None)
        await self.storage.async_save_now()


def _match_pending(
    item: dict[str, Any], deliveries: dict[str, Delivery], candidates: list[str]
) -> str | None:
    """A newly listed package that is the pending add (same carrier, same number or name)."""
    number = normalize_number(item.get("tracking_number", ""))
    for key in candidates:
        delivery = deliveries[key]
        if delivery.carrier_code != item.get("carrier_code"):
            continue
        if normalize_number(delivery.tracking_number) == number:
            return key
    for key in candidates:
        delivery = deliveries[key]
        if delivery.carrier_code == item.get("carrier_code") and delivery.description == item.get(
            "description"
        ):
            return key
    return None


def _find_stored(
    items: list[dict[str, Any]], number: str, carrier: str, name: str | None
) -> tuple[str, str] | None:
    """The (tracking number, carrier) Parcel stored for a package, from the web app's list."""
    wanted = normalize_number(number)
    for item in items:
        if (
            item.get("carrier_code") == carrier
            and normalize_number(str(item.get("tracking_number", ""))) == wanted
        ):
            return str(item["tracking_number"]), carrier
    if name:
        named = [
            item
            for item in items
            if item.get("carrier_code") == carrier
            and item.get("label") == name
            and item.get("tracking_number")
        ]
        if named:
            newest = max(named, key=lambda item: str(item.get("date_added") or ""))
            return str(newest["tracking_number"]), carrier
    return None


def _delivered_time(
    delivery: Delivery, latest: TrackingEvent | None, observed: datetime | None
) -> str | None:
    """Best guess for when a package was delivered."""
    if delivery.status_code != DELIVERED:
        return None
    if latest and latest.when:
        return latest.when.isoformat()
    return observed.isoformat() if observed else None
