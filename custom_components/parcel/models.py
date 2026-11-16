"""Deliveries as Home Assistant sees them, parsed from Parcel's API."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
import re
from typing import Any

from homeassistant.util import dt as dt_util

# Parcel's status codes (from its API docs) as slugs used for entity states.
STATUS_SLUGS: dict[int, str] = {
    0: "delivered",
    1: "stalled",
    2: "in_transit",
    3: "ready_for_pickup",
    4: "out_for_delivery",
    5: "not_found",
    6: "failed_attempt",
    7: "exception",
    8: "label_created",
}
STATUS_OPTIONS: list[str] = list(STATUS_SLUGS.values())
DELIVERED = 0
STALLED = 1
IN_TRANSIT = 2
READY_FOR_PICKUP = 3
OUT_FOR_DELIVERY = 4
NOT_FOUND = 5
FAILED_ATTEMPT = 6
EXCEPTION = 7
LABEL_CREATED = 8
ATTENTION_CODES = frozenset({STALLED, FAILED_ATTEMPT, EXCEPTION})

# Tracking-number shapes for common carriers, used to suggest a carrier.
# Patterns are written so they work both in Python and in the panel's JavaScript.
CARRIER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^1Z[0-9A-Z]{16}$", "ups"),
    (r"^(91|92|93|94|95)[0-9]{18,20}$", "usps"),
    (r"^[A-Z]{2}[0-9]{9}US$", "usps"),
    (r"^TBA[0-9]{12}$", "amzlus"),
    (r"^W[0-9]{9,10}$", "apple"),
    (r"^[CD][0-9]{14}$", "ont"),
    (r"^([0-9]{12}|[0-9]{15}|96[0-9]{20})$", "fedex"),
    (r"^[0-9]{10}$", "dhl"),
)
_CARRIER_RES = tuple((re.compile(p), code) for p, code in CARRIER_PATTERNS)

# An icon for each package, guessed from words in its name. People can pick another.
# Patterns are case-insensitive and work in both Python and JavaScript.
DEFAULT_ICON = "mdi:package-variant-closed"
ICON_RULES: tuple[tuple[str, str], ...] = (
    (r"coffee|espresso|grinder|kettle|\bmug", "mdi:coffee"),
    (r"\btea\b", "mdi:tea"),
    (r"shoe|sneaker|boot|sandal|slipper", "mdi:shoe-sneaker"),
    (r"lamp|bulb|light", "mdi:desk-lamp"),
    (r"extension cord|power strip|outlet|surge|\bplug", "mdi:power-plug-outline"),
    (r"book|guide|novel|magazine|journal", "mdi:book-open-page-variant"),
    (r"laptop|computer|keyboard|mouse|monitor|macbook|tablet|ipad", "mdi:laptop"),
    (r"phone|charger|cable|airtag", "mdi:cellphone"),
    (r"headphone|earbud|airpod|speaker", "mdi:headphones"),
    (r"camera|lens|tripod", "mdi:camera"),
    (r"print|frame|poster|\bart\b|canvas|painting", "mdi:image-frame"),
    (r"plant|seed|garden|soil|fertili|flower", "mdi:sprout"),
    (r"vitamin|pill|medic|supplement|pharm", "mdi:pill"),
    (
        r"jacket|shirt|dress|pants|jeans|hoodie|coat|sweater|sock|cloth|apparel",
        "mdi:tshirt-crew",
    ),
    (r"filter|water", "mdi:water-outline"),
    (r"board game|lego|toy|puzzle", "mdi:toy-brick"),
    (
        r"controller|console|video game|playstation|xbox|nintendo|\bgame",
        "mdi:gamepad-variant",
    ),
    (r"gift|present|birthday", "mdi:gift"),
    (r"watch", "mdi:watch"),
    (
        r"\bdog\b|\bcat\b|\bpet|puppy|kitten|purina|pedigree|\bbreed\b|leash|litter|kibble",
        "mdi:paw",
    ),
    (r"tool|drill|hammer|wrench|screw", "mdi:hammer-wrench"),
    (r"\bpan\b|\bpot\b|kitchen|knife|cook|blender", "mdi:pot-steam"),
    (r"wine", "mdi:glass-wine"),
    (r"food|snack|grocer|candy|chocolate", "mdi:food-apple"),
    (r"\btv\b|television", "mdi:television"),
    (r"battery|power bank", "mdi:battery-charging"),
    (r"\bcase\b", "mdi:cellphone"),
)
ICON_CHOICES: tuple[str, ...] = (
    "mdi:package-variant-closed",
    "mdi:gift",
    "mdi:tshirt-crew",
    "mdi:shoe-sneaker",
    "mdi:book-open-page-variant",
    "mdi:cellphone",
    "mdi:laptop",
    "mdi:headphones",
    "mdi:camera",
    "mdi:coffee",
    "mdi:pot-steam",
    "mdi:sprout",
    "mdi:pill",
    "mdi:toy-brick",
    "mdi:paw",
    "mdi:hammer-wrench",
    "mdi:image-frame",
    "mdi:desk-lamp",
    "mdi:power-plug-outline",
)
_ICON_RES = tuple((re.compile(p, re.IGNORECASE), icon) for p, icon in ICON_RULES)

# Dates Parcel sends without a timezone, in the formats seen or likely from carriers.
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y",
    "%B %d, %Y %I:%M %p",
    "%B %d, %Y",
    "%d %B %Y %H:%M",
    "%d %B %Y",
)


def guess_icon(name: str | None) -> str:
    """Pick an icon from words in a package name."""
    text = name or ""
    for pattern, icon in _ICON_RES:
        if pattern.search(text):
            return icon
    return DEFAULT_ICON


def normalize_number(number: str) -> str:
    """Tracking number without spaces or dashes, uppercased, for matching."""
    return re.sub(r"[\s-]", "", number).upper()


def detect_carriers(number: str, known: Iterable[str] | None = None) -> list[str]:
    """Carrier codes whose tracking-number format matches, most likely first."""
    cleaned = normalize_number(number)
    found: list[str] = []
    allowed = set(known) if known is not None else None
    for pattern, code in _CARRIER_RES:
        if pattern.match(cleaned) and code not in found and (allowed is None or code in allowed):
            found.append(code)
    return found


def parse_parcel_datetime(value: Any, tz: tzinfo) -> datetime | None:
    """Parse a Parcel date or timestamp. Returns None for blanks and placeholders like "--//--"."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return dt_util.utc_from_timestamp(float(value))
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not any(ch.isdigit() for ch in text):
        return None
    parsed = dt_util.parse_datetime(text)
    if parsed is None:
        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(slots=True, frozen=True)
class TrackingEvent:
    """One update from the carrier."""

    text: str
    when: datetime | None
    when_text: str | None
    location: str | None
    additional: str | None

    @property
    def signature(self) -> str:
        """Identity used to notice new updates."""
        return f"{self.text}|{self.when_text or ''}|{self.location or ''}"

    def as_dict(self) -> dict[str, Any]:
        """Serialize for the panel and attributes."""
        return {
            "event": self.text,
            "date": self.when.isoformat() if self.when else None,
            "date_text": None if self.when else self.when_text,
            "location": self.location,
            "additional": self.additional,
        }


@dataclass(slots=True, frozen=True)
class Delivery:
    """A delivery as returned by Parcel."""

    key: str
    tracking_number: str
    carrier_code: str
    description: str
    status_code: int
    events: tuple[TrackingEvent, ...]
    extra_information: str | None
    eta_start: datetime | None
    eta_end: datetime | None
    eta_date: date | None

    @classmethod
    def from_api(cls, raw: Mapping[str, Any], tz: tzinfo) -> Delivery:
        """Build from one item of Parcel's deliveries list."""
        tracking_number = str(raw["tracking_number"]).strip()
        carrier_code = str(raw["carrier_code"]).strip()
        try:
            status_code = int(raw.get("status_code", NOT_FOUND))
        except (TypeError, ValueError):
            status_code = NOT_FOUND
        events: list[TrackingEvent] = []
        for item in raw.get("events") or []:
            if not isinstance(item, Mapping):
                continue
            text = _clean(item.get("event"))
            if not text:
                continue
            when_text = _clean(item.get("date"))
            events.append(
                TrackingEvent(
                    text=text,
                    when=parse_parcel_datetime(when_text, tz),
                    when_text=when_text
                    if when_text and any(ch.isdigit() for ch in when_text)
                    else None,
                    location=_clean(item.get("location")),
                    additional=_clean(item.get("additional")),
                )
            )
        eta_start, eta_end, eta_date = _parse_eta(raw, tz)
        return cls(
            key=f"{carrier_code}:{tracking_number}",
            tracking_number=tracking_number,
            carrier_code=carrier_code,
            description=_clean(raw.get("description")) or tracking_number,
            status_code=status_code,
            events=tuple(events),
            extra_information=_clean(raw.get("extra_information")),
            eta_start=eta_start,
            eta_end=eta_end,
            eta_date=eta_date,
        )

    @property
    def status(self) -> str:
        """Status slug."""
        return STATUS_SLUGS.get(self.status_code, "not_found")

    @property
    def is_active(self) -> bool:
        """Still on its way (not delivered)."""
        return self.status_code != DELIVERED

    @property
    def needs_attention(self) -> bool:
        """Missed delivery, delivery problem or no recent updates."""
        return self.status_code in ATTENTION_CODES

    @property
    def latest_event(self) -> TrackingEvent | None:
        """Most recent carrier update (Parcel lists newest first)."""
        return self.events[0] if self.events else None

    def expected_day(self, tz: tzinfo) -> date | None:
        """Local date the package is expected, if known."""
        if self.eta_date:
            return self.eta_date
        when = self.eta_start or self.eta_end
        return when.astimezone(tz).date() if when else None

    def expected_sort_time(self, tz: tzinfo) -> datetime | None:
        """A comparable moment for sorting by expected arrival."""
        if self.eta_start or self.eta_end:
            return self.eta_start or self.eta_end
        if self.eta_date:
            return datetime.combine(self.eta_date, time(0, 0), tzinfo=tz)
        return None

    def as_dict(self) -> dict[str, Any]:
        """Serialize for the panel, attributes and diagnostics."""
        return {
            "key": self.key,
            "tracking_number": self.tracking_number,
            "carrier_code": self.carrier_code,
            "description": self.description,
            "status_code": self.status_code,
            "status": self.status,
            "eta_start": self.eta_start.isoformat() if self.eta_start else None,
            "eta_end": self.eta_end.isoformat() if self.eta_end else None,
            "eta_date": self.eta_date.isoformat() if self.eta_date else None,
            "extra_information": self.extra_information,
            "events": [event.as_dict() for event in self.events],
        }


def _parse_eta(
    raw: Mapping[str, Any], tz: tzinfo
) -> tuple[datetime | None, datetime | None, date | None]:
    """Expected window, or a date with no time ("2026-11-16 00:00:00" means a date only)."""
    has_timestamp = raw.get("timestamp_expected") is not None
    start = parse_parcel_datetime(raw.get("timestamp_expected"), tz) or parse_parcel_datetime(
        raw.get("date_expected"), tz
    )
    end = parse_parcel_datetime(raw.get("timestamp_expected_end"), tz) or parse_parcel_datetime(
        raw.get("date_expected_end"), tz
    )
    if start is None and end is None:
        return None, None, None
    if start is not None and not has_timestamp:
        local_start = start.astimezone(tz)
        if local_start.time() == time(0, 0) and (
            end is None or end.astimezone(tz).time() >= time(23, 59)
        ):
            return None, None, local_start.date()
    if start is not None and end is not None and end < start:
        end = None
    return start, end, None


def join_names(names: list[str]) -> str:
    """'A', 'A and B', 'A, B and C'."""
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"
