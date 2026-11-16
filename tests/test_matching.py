"""Telling packages apart: pending adds, and what Parcel's web app holds for a delete."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .conftest import raw
from custom_components.parcel.matching import (
    delivered_time,
    find_stored,
    lists_any,
    match_pending,
    same_package,
    split_key,
)
from custom_components.parcel.models import Delivery


def web(number: str, carrier: str, label: str, added: str = "") -> dict[str, Any]:
    """One package as Parcel's web app lists it."""
    return {"tracking_number": number, "carrier_code": carrier, "label": label, "date_added": added}


def listed(number: str, carrier: str, name: str, status: int = 2) -> Delivery:
    return Delivery.from_api(raw(number, carrier, name, status), UTC)


def test_the_number_decides() -> None:
    """Carrier and number find the package, whatever case or spacing the number has."""
    items = [web("1Z999AA10123456784", "ups", "Coffee grinder"), web("TBA1", "amzlus", "Amazon")]
    assert find_stored(items, "1z 999-aa1 0123456784", "ups") == ("1Z999AA10123456784", "ups")
    assert find_stored(items, "1Z999AA10123456784", "fedex") is None


def test_a_listed_package_is_never_found_by_its_name() -> None:
    """Deleted in the app already: a different package with the same name is left alone."""
    items = [web("TBA000000000002", "amzlus", "Amazon")]
    assert find_stored(items, "TBA000000000001", "amzlus") is None


def test_an_add_parcel_has_not_listed_yet_is_found_by_name() -> None:
    """Parcel stores its own number for a placeholder, so the name stands in for it."""
    items = [web("450000000000000000001", "pholder", "Test placeholder", "2026-11-15")]
    assert find_stored(items, "HATEST1", "pholder", unlisted_name="Test placeholder") == (
        "450000000000000000001",
        "pholder",
    )


def test_the_name_never_picks_a_package_that_is_already_listed() -> None:
    """An older package with the same name isn't mistaken for the new add."""
    items = [web("TBA000000000002", "amzlus", "Amazon", "2026-11-01")]
    assert (
        find_stored(
            items,
            "TBA000000000009",
            "amzlus",
            unlisted_name="Amazon",
            listed_numbers={"TBA000000000002"},
        )
        is None
    )


def test_the_newest_unlisted_package_wins_when_names_repeat() -> None:
    items = [
        web("111", "pholder", "Gift", "2026-11-10 09:00:00"),
        web("222", "pholder", "Gift", "2026-11-15 09:00:00"),
    ]
    assert find_stored(items, "X", "pholder", unlisted_name="Gift") == ("222", "pholder")


def test_pending_add_matches_by_number_then_by_name() -> None:
    deliveries = {
        d.key: d
        for d in (
            listed("1Z999AA10123456799", "ups", "Desk lamp"),
            listed("450000000000000000001", "pholder", "Test placeholder"),
        )
    }
    candidates = list(deliveries)
    typed = {
        "tracking_number": "1z999aa10123456799",
        "carrier_code": "ups",
        "description": "Lamp",
        "added_at": "2026-11-15T00:00:00+00:00",
    }
    assert match_pending(typed, deliveries, candidates) == "ups:1Z999AA10123456799"
    placeholder = {**typed, "tracking_number": "HATEST1", "carrier_code": "pholder"}
    assert match_pending(placeholder, deliveries, candidates) is None
    placeholder["description"] = "Test placeholder"
    assert match_pending(placeholder, deliveries, candidates) == "pholder:450000000000000000001"
    # A package that was already known is not a candidate.
    assert match_pending(typed, deliveries, []) is None


def test_keys_compare_without_regard_to_format() -> None:
    assert split_key("ups:1Z999") == ("ups", "1Z999")
    assert same_package("ups:1Z999AA10123456784", "ups", "1z 999-aa1 0123456784")
    assert not same_package("ups:1Z999AA10123456784", "fedex", "1Z999AA10123456784")


def test_delivered_time_prefers_the_carriers_own() -> None:
    seen = datetime(2026, 11, 16, 15, 0, tzinfo=UTC)
    in_transit = listed("A", "ups", "A", 2)
    assert delivered_time(in_transit, None, seen) is None
    scanned = Delivery.from_api(
        raw("B", "ups", "B", 0, events=[{"event": "Delivered", "date": "2026-11-16 14:02:00"}]),
        UTC,
    )
    assert delivered_time(scanned, scanned.latest_event, seen) == "2026-11-16T14:02:00+00:00"
    unscanned = listed("C", "ups", "C", 0)
    assert delivered_time(unscanned, None, seen) == seen.isoformat()
    assert delivered_time(unscanned, None, None) is None


def test_only_a_placeholder_is_found_by_name() -> None:
    """Parcel keeps the number it was given for every other carrier, so a name proves nothing."""
    items = [web("1Z999AA19999999999", "ups", "Running shoes", "2025-03-01 09:00:00")]
    assert find_stored(items, "1Z999AA10000000001", "ups", unlisted_name="Running shoes") is None


def test_a_delivered_placeholder_is_not_the_new_one() -> None:
    """An older placeholder with the same name that was marked delivered is passed over."""
    old = {
        **web("450000000000000000002", "pholder", "Birthday gift", "2025-12-01"),
        "status_code": 0,
    }
    new = web("450000000000000000003", "pholder", "Birthday gift", "2026-11-16")
    assert find_stored([old], "HATEST3", "pholder", unlisted_name="Birthday gift") is None
    assert find_stored([old, new], "HATEST3", "pholder", unlisted_name="Birthday gift") == (
        "450000000000000000003",
        "pholder",
    )


def test_whether_a_list_holds_any_of_the_accounts_packages() -> None:
    items = [web("1Z999AA10123456784", "ups", "Coffee grinder"), {"label": "no number"}]
    assert lists_any(items, {"1Z999AA10123456784"})
    assert lists_any([web("1z 999-aa1 0123456784", "ups", "x")], {"1Z999AA10123456784"})
    assert not lists_any(items, {"TBA312345678901"})
    assert not lists_any([], {"TBA312345678901"})
