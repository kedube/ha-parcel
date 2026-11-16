"""Matching packages between Home Assistant's records and Parcel's lists. No I/O."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import datetime
from typing import Any

from .const import PLACEHOLDER_CARRIER
from .models import DELIVERED, Delivery, TrackingEvent, normalize_number
from .storage import PendingRecord


def split_key(key: str) -> tuple[str, str]:
    """A package key ("carrier:number") as (carrier, number)."""
    carrier, _, number = key.partition(":")
    return carrier, number


def same_package(key: str, carrier_code: str, tracking_number: str) -> bool:
    """Whether a key names this carrier and number (spaces, dashes and case aside)."""
    carrier, number = split_key(key)
    return carrier == carrier_code and normalize_number(number) == normalize_number(tracking_number)


def match_pending(
    item: PendingRecord, deliveries: Mapping[str, Delivery], candidates: Sequence[str]
) -> str | None:
    """The newly listed package that is this pending add.

    Same carrier and same number. Failing that, same carrier and same name, because
    Parcel stores a number of its own for placeholder packages.
    """
    carrier = item.get("carrier_code")
    number = normalize_number(item.get("tracking_number", ""))
    for key in candidates:
        delivery = deliveries[key]
        if (
            delivery.carrier_code == carrier
            and normalize_number(delivery.tracking_number) == number
        ):
            return key
    for key in candidates:
        delivery = deliveries[key]
        if delivery.carrier_code == carrier and delivery.description == item.get("description"):
            return key
    return None


def find_stored(
    items: Sequence[Mapping[str, Any]],
    number: str,
    carrier: str,
    *,
    unlisted_name: str | None = None,
    listed_numbers: Collection[str] = (),
) -> tuple[str, str] | None:
    """The (tracking number, carrier) Parcel's web app holds for a package.

    The number decides. Parcel numbers placeholder packages itself, so for a
    placeholder it hasn't listed through its API yet (pass its name as unlisted_name)
    the name is tried as well. Even then, a package that is already listed (normalized
    numbers in listed_numbers) or already delivered is never picked, so an older
    package that merely shares the name can't be mistaken for the one looked up.
    """
    wanted = normalize_number(number)
    for item in items:
        if (
            item.get("carrier_code") == carrier
            and normalize_number(str(item.get("tracking_number", ""))) == wanted
        ):
            return str(item["tracking_number"]), carrier
    if unlisted_name is None or carrier != PLACEHOLDER_CARRIER:
        return None
    named = [
        item
        for item in items
        if item.get("carrier_code") == carrier
        and item.get("label") == unlisted_name
        and item.get("tracking_number")
        and item.get("status_code") != DELIVERED
        and normalize_number(str(item["tracking_number"])) not in listed_numbers
    ]
    if not named:
        return None
    newest = max(named, key=lambda item: str(item.get("date_added") or ""))
    return str(newest["tracking_number"]), carrier


def lists_any(items: Sequence[Mapping[str, Any]], numbers: Collection[str]) -> bool:
    """Whether a web-app list holds any of these normalized tracking numbers.

    Every package on its way is in the account's web list, so a list holding none of
    the account's packages is another account's (or didn't come through whole).
    """
    return any(normalize_number(str(item.get("tracking_number", ""))) in numbers for item in items)


def delivered_time(
    delivery: Delivery, latest: TrackingEvent | None, observed: datetime | None
) -> str | None:
    """Best guess for when a package was delivered."""
    if delivery.status_code != DELIVERED:
        return None
    if latest and latest.when:
        return latest.when.isoformat()
    return observed.isoformat() if observed else None
