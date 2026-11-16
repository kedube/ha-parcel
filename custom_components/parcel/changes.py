"""Noticing what changed between two checks, and putting it into words. No I/O."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .const import (
    EVENT_ADDED,
    EVENT_DELIVERED,
    EVENT_IN_TRANSIT,
    EVENT_LABEL_CREATED,
    EVENT_NEEDS_ATTENTION,
    EVENT_OUT_FOR_DELIVERY,
    EVENT_READY_FOR_PICKUP,
    EVENT_REMOVED,
    EVENT_UPDATE,
)
from .matching import delivered_time
from .models import (
    DELIVERED,
    EXCEPTION,
    FAILED_ATTEMPT,
    IN_TRANSIT,
    LABEL_CREATED,
    NOT_FOUND,
    OUT_FOR_DELIVERY,
    READY_FOR_PICKUP,
    STALLED,
    Delivery,
)
from .storage import KnownPackage

# The event fired when a package moves to each of Parcel's statuses.
STATUS_EVENTS: dict[int, str] = {
    DELIVERED: EVENT_DELIVERED,
    STALLED: EVENT_NEEDS_ATTENTION,
    IN_TRANSIT: EVENT_IN_TRANSIT,
    READY_FOR_PICKUP: EVENT_READY_FOR_PICKUP,
    OUT_FOR_DELIVERY: EVENT_OUT_FOR_DELIVERY,
    NOT_FOUND: EVENT_UPDATE,
    FAILED_ATTEMPT: EVENT_NEEDS_ATTENTION,
    EXCEPTION: EVENT_NEEDS_ATTENTION,
    LABEL_CREATED: EVENT_LABEL_CREATED,
}

# Why a package is no longer tracked.
REASON_DELETED = "deleted"
REASON_NOT_LISTED = "no_longer_listed"


@dataclass(slots=True, frozen=True)
class Change:
    """One thing that happened to a package."""

    kind: str  # an event type, such as "delivered" or "removed"
    delivery: Delivery  # the package now; for a removal, as it was last known
    previous_status: int | None
    reason: str | None = None  # for removals: REASON_DELETED or REASON_NOT_LISTED


def event_message(kind: str, delivery: Delivery, carrier: str) -> str:
    """A sentence ready to use in a notification."""
    name = delivery.description
    latest = delivery.latest_event
    if kind == EVENT_ADDED:
        return f"Now tracking {name}"
    if kind == EVENT_LABEL_CREATED:
        return f"{name} has a shipping label. {carrier} doesn't have it yet"
    if kind == EVENT_IN_TRANSIT:
        return f"{name} is on the way"
    if kind == EVENT_OUT_FOR_DELIVERY:
        return f"{name} is out for delivery"
    if kind == EVENT_READY_FOR_PICKUP:
        where = f" at {latest.location}" if latest and latest.location else ""
        return f"{name} is ready for pickup{where}"
    if kind == EVENT_DELIVERED:
        return f"{name} was delivered"
    if kind == EVENT_NEEDS_ATTENTION:
        if delivery.status_code == FAILED_ATTEMPT:
            return f"{carrier} missed the delivery of {name}"
        if delivery.status_code == EXCEPTION:
            detail = f": {latest.text}" if latest else ""
            return f"{name} has a delivery problem{detail}"
        if delivery.status_code == STALLED:
            return f"{name} hasn't had an update in a while"
    if kind == EVENT_REMOVED:
        return f"{name} is no longer tracked"
    if latest:
        return f"{name}: {latest.text}"
    return f"{name} has an update"


def last_known(key: str, record: Mapping[str, Any]) -> Delivery:
    """A package that is gone, rebuilt from what was remembered about it."""
    number = str(record.get("tracking_number") or "")
    try:
        status = int(record.get("status", NOT_FOUND))
    except (TypeError, ValueError):
        status = NOT_FOUND
    return Delivery(
        key=key,
        tracking_number=number,
        carrier_code=str(record.get("carrier_code") or ""),
        description=str(record.get("description") or number),
        status_code=status,
        events=(),
        extra_information=None,
        eta_start=None,
        eta_end=None,
        eta_date=None,
    )


def removal(key: str, record: Mapping[str, Any], reason: str) -> Change:
    """The change for a package that is no longer tracked."""
    gone = last_known(key, record)
    return Change(EVENT_REMOVED, gone, gone.status_code, reason)


def detect_changes(
    known: dict[str, KnownPackage],
    deliveries: Mapping[str, Delivery],
    now: datetime,
    *,
    announce: bool,
    keep: Collection[str] = (),
) -> list[Change]:
    """Compare Parcel's list with what was known, and bring `known` up to date.

    Nothing is announced on the very first check (announce=False), when every
    package would otherwise count as new. Packages in keep are missing from this
    reply but not yet taken as gone, so they are neither removed nor announced.
    """
    changes: list[Change] = []
    for key, delivery in deliveries.items():
        latest = delivery.latest_event
        signature = latest.signature if latest else ""
        previous = known.get(key)
        if previous is None:
            known[key] = {
                "status": delivery.status_code,
                "first_seen": now.isoformat(),
                "delivered_at": delivered_time(delivery, latest, None),
                "event": signature,
                "description": delivery.description,
                "tracking_number": delivery.tracking_number,
                "carrier_code": delivery.carrier_code,
            }
            changes.append(Change(EVENT_ADDED, delivery, None))
            continue
        old_status = previous.get("status")
        previous["description"] = delivery.description
        if old_status != delivery.status_code:
            if delivery.status_code == DELIVERED and not previous.get("delivered_at"):
                previous["delivered_at"] = delivered_time(delivery, latest, now)
            kind = STATUS_EVENTS.get(delivery.status_code, EVENT_UPDATE)
            changes.append(Change(kind, delivery, old_status))
        elif signature and signature != previous.get("event"):
            changes.append(Change(EVENT_UPDATE, delivery, old_status))
        previous["status"] = delivery.status_code
        previous["event"] = signature
    for key in [key for key in known if key not in deliveries and key not in keep]:
        changes.append(removal(key, known.pop(key), REASON_NOT_LISTED))
    return changes if announce else []
