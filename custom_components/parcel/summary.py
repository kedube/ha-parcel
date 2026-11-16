"""The high-level picture: what's out for delivery, arriving today, and next. No I/O."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime

from .models import OUT_FOR_DELIVERY, READY_FOR_PICKUP, Delivery


@dataclass(slots=True, frozen=True)
class Summary:
    """Lists behind the summary sensors, each sorted by expected arrival."""

    out_for_delivery: list[Delivery]
    arriving_today: list[Delivery]
    needs_attention: list[Delivery]
    ready_for_pickup: list[Delivery]
    on_the_way: list[Delivery]
    delivered_today: list[Delivery]
    # The next day anything is expected, and what is expected that day.
    next_day: date | None
    next_day_deliveries: list[Delivery]
    # The next package the carrier gave a time for, and when its window starts.
    next_timed: Delivery | None
    next_timed_at: datetime | None


def build_summary(
    deliveries: Iterable[Delivery],
    delivered_at: Callable[[Delivery], datetime | None],
    now: datetime,
) -> Summary:
    """Sort deliveries into the summary lists. "Today" is the local date of now (aware)."""
    tz = now.tzinfo
    if tz is None:
        raise ValueError("now must be timezone-aware")
    today = now.date()
    far = datetime.max.replace(tzinfo=tz)
    items = sorted(deliveries, key=lambda d: d.expected_sort_time(tz) or far)
    active = [d for d in items if d.is_active]

    def expected_day(delivery: Delivery) -> date | None:
        # Out for delivery means today, whatever date the carrier gave earlier.
        if delivery.status_code == OUT_FOR_DELIVERY:
            return today
        return delivery.expected_day(tz)

    # Still coming, and not held up: (day, package), earliest first.
    upcoming = [
        (day, d)
        for d in active
        if not d.needs_attention and (day := expected_day(d)) is not None and day >= today
    ]
    next_day = min((day for day, _ in upcoming), default=None)
    timed = [
        (when, d)
        for _, d in upcoming
        if (when := d.eta_start or d.eta_end) is not None and when.astimezone(tz).date() >= today
    ]
    next_timed = min(timed, key=lambda pair: pair[0], default=None)

    return Summary(
        out_for_delivery=[d for d in active if d.status_code == OUT_FOR_DELIVERY],
        arriving_today=[d for d in active if not d.needs_attention and expected_day(d) == today],
        needs_attention=[d for d in active if d.needs_attention],
        ready_for_pickup=[d for d in active if d.status_code == READY_FOR_PICKUP],
        on_the_way=[d for d in active if d.status_code != READY_FOR_PICKUP],
        delivered_today=[
            d
            for d in items
            if not d.is_active
            and (when := delivered_at(d)) is not None
            and when.astimezone(tz).date() == today
        ],
        next_day=next_day,
        next_day_deliveries=[d for day, d in upcoming if day == next_day],
        next_timed=next_timed[1] if next_timed else None,
        next_timed_at=next_timed[0] if next_timed else None,
    )
