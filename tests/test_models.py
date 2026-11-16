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
    package_key,
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


def test_placeholder_and_impossible_dates_are_unknown() -> None:
    """Dates far outside the present are stand-ins, and some couldn't even change zone."""
    for value in (
        253402300799,  # 9999-12-31, a common "no date"
        0,  # 1970
        -62135596800,  # the first day of year 1
        "9999-12-31",
        "0001-01-01T00:00:00+05:00",
    ):
        assert parse_parcel_datetime(value, TZ) is None, value
    assert parse_parcel_datetime("2026-11-16 13:00:00", TZ) == datetime(2026, 11, 16, 13, tzinfo=TZ)
    delivery = Delivery.from_api(
        {
            "tracking_number": "1",
            "carrier_code": "usps",
            "status_code": float("inf"),
            "timestamp_expected": 253402300799,
            "date_expected": "0001-01-01T00:00:00+05:00",
        },
        ZoneInfo("Europe/Berlin"),
    )
    assert delivery.status == "not_found"
    assert (delivery.eta_start, delivery.eta_end, delivery.eta_date) == (None, None, None)


def test_icons_for_real_names() -> None:
    """Icons are guessed from words in the name."""
    assert guess_icon("2 Pack Outdoor Extension Cord Cover") == "mdi:power-plug-outline"
    assert guess_icon("Small breed dog food") == "mdi:paw"
    assert guess_icon("Coffee grinder") == "mdi:coffee"
    assert guess_icon("LED Desk Lamp with USB Charging Port") == "mdi:desk-lamp"
    assert guess_icon("Plant food") == "mdi:sprout"
    assert guess_icon("Something else entirely") == "mdi:package-variant-closed"
    assert guess_icon(None) == "mdi:package-variant-closed"


def test_a_word_inside_another_word_does_not_decide_the_icon() -> None:
    """The narrower rule wins: these used to come out as a book, a phone and a lamp."""
    assert guess_icon("MacBook Air 13") == "mdi:laptop"
    assert guess_icon("Chromebook") == "mdi:laptop"
    assert guess_icon("Wireless headphones") == "mdi:headphones"
    assert guess_icon("Lightning to USB-C cable") == "mdi:cellphone"
    assert guess_icon("Flight jacket") == "mdi:tshirt-crew"
    assert guess_icon("LED string lights") == "mdi:desk-lamp"
    assert guess_icon("Art print") == "mdi:image-frame"
    assert guess_icon("Printer ink") == "mdi:package-variant-closed"
    assert guess_icon("Bar stool") == "mdi:package-variant-closed"
    assert guess_icon("Toolbox") == "mdi:hammer-wrench"


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


def test_a_date_that_cannot_exist_is_no_date() -> None:
    """February 30 or hour 25 from a carrier: no date, but the text and the package stay."""
    assert parse_parcel_datetime("2026-02-30 10:00:00", TZ) is None
    assert parse_parcel_datetime("2026-11-16 25:00:00", TZ) is None
    delivery = Delivery.from_api(
        {
            "tracking_number": "1Z999AA10123456784",
            "carrier_code": "ups",
            "description": "Coffee grinder",
            "status_code": 2,
            "events": [{"event": "Arrived", "date": "2026-02-30 10:00:00"}],
            "date_expected": "2026-11-16 25:00:00",
        },
        TZ,
    )
    assert delivery.events[0].when is None
    assert delivery.events[0].when_text == "2026-02-30 10:00:00"
    assert delivery.eta_start is None


def test_each_amazon_shipment_has_a_key_of_its_own() -> None:
    """Parcel tracks Amazon by shipment: the order number plus the shipment ID."""
    assert package_key("amzlus", "113-4567890-1234567", "Ab3Cd9EfG") == (
        "amzlus:113-4567890-1234567@Ab3Cd9EfG"
    )
    assert package_key("amzluk", "205-1234567-7654321", "Hj7Kl2MnP") == (
        "amzluk:205-1234567-7654321@Hj7Kl2MnP"
    )
    # Without a shipment ID, and for other carriers' extra details, the number alone.
    assert package_key("amzlus", "TBA312345678901") == "amzlus:TBA312345678901"
    assert package_key("dpd", "01234567890123", "94107") == "dpd:01234567890123"
    parts = [
        Delivery.from_api(
            {
                "tracking_number": "113-4567890-1234567",
                "carrier_code": "amzlus",
                "description": name,
                "status_code": 2,
                "extra_information": shipment,
            },
            TZ,
        )
        for name, shipment in (("Kettle", "Ab3Cd9EfG"), ("Mugs", "Hj7Kl2MnP"))
    ]
    assert parts[0].key != parts[1].key
