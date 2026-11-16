"""Parsing Parcel's data, icon guesses and carrier detection."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from custom_components.parcel.models import (
    Delivery,
    detect_carriers,
    guess_icon,
    join_names,
    normalize_number,
    parse_parcel_datetime,
)

TZ = ZoneInfo("America/New_York")


def test_date_only_eta_from_midnight() -> None:
    """Parcel's '... 00:00:00' with no end means a day, not midnight."""
    delivery = Delivery.from_api(
        {
            "tracking_number": "TBA1",
            "carrier_code": "amzlus",
            "description": "x",
            "status_code": 2,
            "events": [],
            "date_expected": "2026-11-16 00:00:00",
        },
        TZ,
    )
    assert delivery.eta_date == date(2026, 11, 16)
    assert delivery.eta_start is None and delivery.eta_end is None


def test_window_is_local_time() -> None:
    """Dates without a timezone are in Home Assistant's timezone."""
    delivery = Delivery.from_api(
        {
            "tracking_number": "1",
            "carrier_code": "ups",
            "description": "x",
            "status_code": 4,
            "events": [],
            "date_expected": "2026-11-16 13:00:00",
            "date_expected_end": "2026-11-16 16:00:00",
        },
        TZ,
    )
    assert delivery.eta_start == datetime(2026, 11, 16, 13, 0, tzinfo=TZ)
    assert delivery.eta_end == datetime(2026, 11, 16, 16, 0, tzinfo=TZ)
    assert delivery.eta_date is None


def test_timestamps_win_over_text() -> None:
    """When Parcel sends epoch timestamps, they are exact."""
    delivery = Delivery.from_api(
        {
            "tracking_number": "1",
            "carrier_code": "ups",
            "description": "x",
            "status_code": 2,
            "events": [],
            "date_expected": "2026-11-16 00:00:00",
            "timestamp_expected": 1794841200,
        },
        TZ,
    )
    assert delivery.eta_start is not None
    assert delivery.eta_date is None


def test_placeholder_event_dates_are_unknown() -> None:
    """Amazon events carry '--//--' instead of a date."""
    delivery = Delivery.from_api(
        {
            "tracking_number": "TBA1",
            "carrier_code": "amzlus",
            "description": "x",
            "status_code": 2,
            "events": [{"event": "Shipped", "date": "--//--"}],
        },
        TZ,
    )
    assert delivery.events[0].when is None
    assert delivery.events[0].when_text is None
    assert parse_parcel_datetime("--//--", TZ) is None
    assert parse_parcel_datetime("", TZ) is None


def test_bad_status_and_missing_name() -> None:
    """Odd values don't break parsing."""
    delivery = Delivery.from_api(
        {"tracking_number": " 123 ", "carrier_code": "usps", "status_code": "x", "events": "nope"},
        TZ,
    )
    assert delivery.status == "not_found"
    assert delivery.description == "123"
    assert delivery.key == "usps:123"


def test_icons_for_real_names() -> None:
    """Icons are guessed from words in the name."""
    assert guess_icon("iwillink 2 Pack Outdoor Extension Cord Cover") == "mdi:power-plug-outline"
    assert guess_icon("Purina Pro Plan Small Breed") == "mdi:paw"
    assert guess_icon("Coffee grinder") == "mdi:coffee"
    assert guess_icon("LED Desk Lamp with USB Charging Port") == "mdi:desk-lamp"
    assert guess_icon("Plant food") == "mdi:sprout"
    assert guess_icon("Something else entirely") == "mdi:package-variant-closed"
    assert guess_icon(None) == "mdi:package-variant-closed"


def test_carrier_detection() -> None:
    """Common tracking-number shapes suggest a carrier."""
    assert detect_carriers("1Z 999 AA1 01 2345 6784") == ["ups"]
    assert detect_carriers("9400 1112 0255 5842 3326 70") == ["usps"]
    assert detect_carriers("TBA312345678901") == ["amzlus"]
    assert detect_carriers("781234567890") == ["fedex"]
    assert detect_carriers("W1234567890") == ["apple"]
    assert detect_carriers("1Z999AA10123456784", known={"usps"}) == []
    assert detect_carriers("hello") == []
    assert normalize_number(" 1z-999 ") == "1Z999"


def test_join_names() -> None:
    """Lists read naturally."""
    assert join_names([]) == ""
    assert join_names(["A"]) == "A"
    assert join_names(["A", "B"]) == "A and B"
    assert join_names(["A", "B", "C"]) == "A, B and C"
