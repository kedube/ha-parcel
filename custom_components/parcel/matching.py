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


def web_number(item: Mapping[str, Any]) -> tuple[str, str]:
    """A tracking number in the web app's list: normalized, and the code after its "@".

    The web app adds a code of its own to some numbers. An Amazon order is
    "<order number>@<code>" there, where Parcel's API gives the order number as the
    tracking number and the code as extra_information.
    """
    number, _, code = str(item.get("tracking_number", "")).partition("@")
    return normalize_number(number), code


def lists_number(items: Sequence[Mapping[str, Any]], number: str, carrier: str) -> bool:
    """Whether the web app's list has this carrier and number, with any code or none."""
    wanted = normalize_number(number.partition("@")[0])
    return any(
        item.get("carrier_code") == carrier and web_number(item)[0] == wanted for item in items
    )


def find_stored(
    items: Sequence[Mapping[str, Any]],
    number: str,
    carrier: str,
    *,
    extra: str | None = None,
    unlisted_name: str | None = None,
    listed_numbers: Collection[str] = (),
) -> tuple[str, str] | None:
    """The (tracking number, carrier) Parcel's web app holds for a package.

    The number decides. Where the web app adds a code to it, the code must be the
    package's extra_information (pass it as extra), which tells apart the shipments
    of one Amazon order; a number given with its "@<code>" matches only that one.
    None when no package fits, or when several do and nothing tells them apart.

    Parcel numbers placeholder packages itself, so for a placeholder it hasn't listed
    through its API yet (pass its name as unlisted_name) the name is tried as well.
    Even then, a package that is already listed (normalized numbers in
    listed_numbers) or already delivered is never picked, so an older package that
    merely shares the name can't be mistaken for the one looked up.
    """
    wanted, at, code = number.partition("@")
    wanted = normalize_number(wanted)
    fits = []
    for item in items:
        item_number, item_code = web_number(item)
        if item.get("carrier_code") != carrier or item_number != wanted:
            continue
        if at:
            if item_code == code:
                fits.append(item)
        elif not item_code or not extra or item_code == extra:
            # A code that isn't the package's extra_information is another shipment.
            fits.append(item)
    if len(fits) == 1:
        return str(fits[0]["tracking_number"]), carrier
    if fits or unlisted_name is None or carrier != PLACEHOLDER_CARRIER:
        return None
    named = [
        item
        for item in items
        if item.get("carrier_code") == carrier
        and item.get("label") == unlisted_name
        and item.get("tracking_number")
        and item.get("status_code") != DELIVERED
        and web_number(item)[0] not in listed_numbers
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
    return any(web_number(item)[0] in numbers for item in items)


def delivered_time(
    delivery: Delivery, latest: TrackingEvent | None, observed: datetime | None
) -> str | None:
    """Best guess for when a package was delivered."""
    if delivery.status_code != DELIVERED:
        return None
    if latest and latest.when:
        return latest.when.isoformat()
    return observed.isoformat() if observed else None
