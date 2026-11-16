"""Noticing changes between checks, and the sentences that describe them."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .conftest import raw
from custom_components.parcel.changes import (
    REASON_DELETED,
    REASON_NOT_LISTED,
    STATUS_EVENTS,
    detect_changes,
    event_message,
    last_known,
    removal,
)
from custom_components.parcel.models import STATUS_SLUGS, Delivery

NOW = datetime(2026, 11, 16, 15, 0, tzinfo=UTC)


def listing(*items: dict[str, Any]) -> dict[str, Delivery]:
    deliveries = [Delivery.from_api(item, UTC) for item in items]
    return {delivery.key: delivery for delivery in deliveries}


def kinds(changes: list) -> list[str]:
    return [change.kind for change in changes]


def test_every_status_has_an_event() -> None:
    assert STATUS_EVENTS.keys() == STATUS_SLUGS.keys()


def test_the_first_check_remembers_without_announcing() -> None:
    known: dict = {}
    changes = detect_changes(known, listing(raw("1", "ups", "Lamp", 2)), NOW, announce=False)
    assert changes == []
    assert known["ups:1"]["status"] == 2
    assert known["ups:1"]["first_seen"] == NOW.isoformat()
    assert known["ups:1"]["description"] == "Lamp"


def test_new_changed_updated_and_gone() -> None:
    known: dict = {}
    scan = {"event": "Departed facility", "date": "2026-11-16 09:00:00"}
    before = listing(
        raw("1", "ups", "Lamp", 2),
        raw("2", "ups", "Shoes", 2, events=[scan]),
        raw("3", "ups", "Book", 2),
        raw("4", "ups", "Steady", 2, events=[scan]),
    )
    detect_changes(known, before, NOW, announce=False)

    newer = {"event": "Arrived at facility", "date": "2026-11-16 12:00:00"}
    after = listing(
        raw("1", "ups", "Lamp", 4),  # status changed
        raw("2", "ups", "Shoes", 2, events=[newer, scan]),  # a new carrier update
        raw("4", "ups", "Steady", 2, events=[scan]),  # nothing new
        raw("5", "ups", "Gift", 8),  # new
    )
    changes = {
        change.delivery.key: change for change in detect_changes(known, after, NOW, announce=True)
    }
    assert {key: change.kind for key, change in changes.items()} == {
        "ups:1": "out_for_delivery",
        "ups:2": "update",
        "ups:5": "added",
        "ups:3": "removed",
    }
    assert changes["ups:1"].previous_status == 2
    assert changes["ups:5"].previous_status is None
    assert changes["ups:3"].reason == REASON_NOT_LISTED
    assert changes["ups:3"].delivery.description == "Book"
    assert set(known) == {"ups:1", "ups:2", "ups:4", "ups:5"}

    # Checking again with nothing different says nothing.
    assert detect_changes(known, after, NOW, announce=True) == []


def test_delivery_time_is_kept_from_the_first_time_it_is_seen() -> None:
    known: dict = {}
    detect_changes(known, listing(raw("1", "ups", "Lamp", 4)), NOW, announce=False)
    assert known["ups:1"]["delivered_at"] is None
    changes = detect_changes(known, listing(raw("1", "ups", "Lamp", 0)), NOW, announce=True)
    assert kinds(changes) == ["delivered"]
    assert known["ups:1"]["delivered_at"] == NOW.isoformat()
    # A later check doesn't move it.
    later = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
    known["ups:1"]["status"] = 2
    detect_changes(known, listing(raw("1", "ups", "Lamp", 0)), later, announce=True)
    assert known["ups:1"]["delivered_at"] == NOW.isoformat()


def test_each_kind_of_trouble_is_needs_attention() -> None:
    known: dict = {}
    detect_changes(known, listing(raw("1", "ups", "Lamp", 2)), NOW, announce=False)
    for status in (1, 6, 7):
        known["ups:1"]["status"] = 2
        changes = detect_changes(
            known, listing(raw("1", "ups", "Lamp", status)), NOW, announce=True
        )
        assert kinds(changes) == ["needs_attention"]


def test_sentences() -> None:
    def said(kind: str, status: int, **extra: Any) -> str:
        delivery = Delivery.from_api(raw("1", "ups", "Framed print", status, **extra), UTC)
        return event_message(kind, delivery, "UPS")

    at_shop = [{"event": "Ready", "date": "2026-11-16 09:00:00", "location": "Main St Locker"}]
    damaged = [{"event": "Package damaged", "date": "2026-11-16 09:00:00"}]
    assert said("added", 2) == "Now tracking Framed print"
    assert said("label_created", 8) == "Framed print has a shipping label. UPS doesn't have it yet"
    assert said("in_transit", 2) == "Framed print is on the way"
    assert said("out_for_delivery", 4) == "Framed print is out for delivery"
    assert said("ready_for_pickup", 3) == "Framed print is ready for pickup"
    assert said("ready_for_pickup", 3, events=at_shop) == (
        "Framed print is ready for pickup at Main St Locker"
    )
    assert said("delivered", 0) == "Framed print was delivered"
    assert said("needs_attention", 6) == "UPS missed the delivery of Framed print"
    assert said("needs_attention", 7, events=damaged) == (
        "Framed print has a delivery problem: Package damaged"
    )
    assert said("needs_attention", 1) == "Framed print hasn't had an update in a while"
    assert said("removed", 2) == "Framed print is no longer tracked"
    assert said("update", 2, events=damaged) == "Framed print: Package damaged"
    assert said("update", 2) == "Framed print has an update"


def test_a_removed_package_is_described_from_what_was_remembered() -> None:
    record = {"tracking_number": "1Z9", "carrier_code": "ups", "description": "Lamp", "status": 4}
    change = removal("ups:1Z9", record, REASON_DELETED)
    assert (change.kind, change.reason, change.previous_status) == ("removed", "deleted", 4)
    assert change.delivery.description == "Lamp"
    assert change.delivery.status == "out_for_delivery"
    # Very little remembered still makes a usable event.
    sparse = last_known("ups:1Z9", {"tracking_number": "1Z9", "status": "odd"})
    assert (sparse.description, sparse.carrier_code, sparse.status) == ("1Z9", "", "not_found")
