"""The summary behind the sensors: today, the next day, and the next known time."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from .conftest import raw
from custom_components.parcel.models import Delivery
from custom_components.parcel.summary import build_summary

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=TZ)  # a Monday morning


def package(name: str, status: int, **extra: Any) -> Delivery:
    return Delivery.from_api(raw(f"NUM{name}", "ups", name, status, **extra), TZ)


def nothing_delivered(_delivery: Delivery) -> None:
    return None


def test_a_day_without_a_time_is_a_day_not_midnight() -> None:
    """A carrier that only gives the day fills the day; there is no time to report."""
    summary = build_summary(
        [package("Dog food", 2, date_expected="2026-11-17 00:00:00")], nothing_delivered, NOW
    )
    assert summary.next_day == date(2026, 11, 17)
    assert [d.description for d in summary.next_day_deliveries] == ["Dog food"]
    assert summary.next_timed is None
    assert summary.next_timed_at is None
    assert summary.arriving_today == []


def test_the_next_known_time_can_be_later_than_the_next_day() -> None:
    summary = build_summary(
        [
            package("Dog food", 2, date_expected="2026-11-16 00:00:00"),
            package(
                "Coffee grinder",
                2,
                date_expected="2026-11-17 13:00:00",
                date_expected_end="2026-11-17 16:00:00",
            ),
        ],
        nothing_delivered,
        NOW,
    )
    assert summary.next_day == date(2026, 11, 16)
    assert [d.description for d in summary.next_day_deliveries] == ["Dog food"]
    assert summary.next_timed is not None
    assert summary.next_timed.description == "Coffee grinder"
    assert summary.next_timed_at == datetime(2026, 11, 17, 13, 0, tzinfo=TZ)
    assert [d.description for d in summary.arriving_today] == ["Dog food"]


def test_out_for_delivery_means_today() -> None:
    """Whatever date the carrier gave before, a package on the truck arrives today."""
    summary = build_summary(
        [
            package("No date", 4),
            package("Old date", 4, date_expected="2026-11-14 00:00:00"),
            package("Tomorrow", 2, date_expected="2026-11-17 00:00:00"),
        ],
        nothing_delivered,
        NOW,
    )
    assert sorted(d.description for d in summary.arriving_today) == ["No date", "Old date"]
    assert sorted(d.description for d in summary.out_for_delivery) == ["No date", "Old date"]
    assert summary.next_day == date(2026, 11, 16)
    assert len(summary.next_day_deliveries) == 2


def test_held_up_and_overdue_packages_are_not_what_comes_next() -> None:
    summary = build_summary(
        [
            package("Missed", 6, date_expected="2026-11-16 00:00:00"),
            package("Overdue", 2, date_expected="2026-11-13 00:00:00"),
            package("At the shop", 3),
        ],
        nothing_delivered,
        NOW,
    )
    assert summary.next_day is None
    assert summary.next_day_deliveries == []
    assert [d.description for d in summary.needs_attention] == ["Missed"]
    assert [d.description for d in summary.ready_for_pickup] == ["At the shop"]
    assert sorted(d.description for d in summary.on_the_way) == ["Missed", "Overdue"]


def test_delivered_today_uses_the_local_day() -> None:
    late_last_night = datetime(2026, 11, 15, 23, 30, tzinfo=TZ)
    this_morning = datetime(2026, 11, 16, 8, 15, tzinfo=TZ)
    times = {"Yesterday": late_last_night, "Today": this_morning}
    summary = build_summary(
        [package("Yesterday", 0), package("Today", 0), package("Unknown", 0)],
        lambda d: times.get(d.description),
        NOW,
    )
    assert [d.description for d in summary.delivered_today] == ["Today"]
    assert summary.on_the_way == []


def test_now_needs_a_time_zone() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_summary([], nothing_delivered, datetime(2026, 11, 16, 9, 0))
