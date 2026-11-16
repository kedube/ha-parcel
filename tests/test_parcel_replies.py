"""What Parcel's replies can hold, and what the integration makes of them."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from homeassistant.core import HomeAssistant

from .conftest import check_until_gone, raw
from .test_init import setup
from custom_components.parcel.const import DOMAIN, EVENT_PACKAGE_UPDATE
from custom_components.parcel.models import Delivery, listing_key

UPS = "1Z999AA10123456784"
UPS_KEY = f"ups:{UPS}"
ORDER = "113-4567890-1234567"
TZ = ZoneInfo("America/New_York")


async def check(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


def kinds(events: list) -> list[str]:
    return [event.data["type"] for event in events]


# A reply that leaves packages out ---------------------------------------------


async def test_a_reply_that_leaves_everything_out_is_not_taken_at_its_word(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Once, Parcel lists nothing: nothing is announced, shown differently or forgotten."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    coordinator.async_set_icon(UPS_KEY, "mdi:robot")
    first_seen = coordinator.storage.known[UPS_KEY]["first_seen"]
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    listed = list(deliveries)

    deliveries.clear()
    await check(hass, config_entry)
    assert UPS_KEY in coordinator.data.deliveries
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"

    deliveries.extend(listed)
    await check(hass, config_entry)
    assert events == []
    assert coordinator.icon_for(UPS_KEY, "Coffee grinder") == "mdi:robot"
    assert coordinator.storage.known[UPS_KEY]["first_seen"] == first_seen


async def test_a_package_gone_for_good_is_removed_once(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, config_entry)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries.pop(0)
    await check_until_gone(hass, config_entry, freezer)
    await check_until_gone(hass, config_entry, freezer)
    assert kinds(events) == ["removed"]
    assert UPS_KEY not in config_entry.runtime_data.data.deliveries
    assert hass.states.get("sensor.parcel_coffee_grinder") is None


# One package, recognized under another key -----------------------------------


async def test_a_number_written_differently_is_the_same_package(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    coordinator.async_set_icon(UPS_KEY, "mdi:robot")
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries[0]["tracking_number"] = "1Z 999 AA1 01 2345 6784"
    await check(hass, config_entry)
    assert events == []
    assert coordinator.icon_for("ups:1Z 999 AA1 01 2345 6784", "Coffee grinder") == "mdi:robot"
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"
    assert hass.states.get("sensor.parcel_coffee_grinder_2") is None


async def test_a_deleted_package_stays_hidden_whatever_spelling_parcel_uses(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    stored = {"tracking_number": UPS, "carrier_code": "ups", "label": "Coffee grinder"}
    mock_parcel.web_list.side_effect = [[stored], []]
    await coordinator.async_delete_package(UPS_KEY)
    deliveries[0]["tracking_number"] = "1z999aa10123456784"  # Parcel's cache, respelled
    await check(hass, config_entry)
    assert all(d.tracking_number.upper() != UPS for d in coordinator.data.deliveries.values())


async def test_a_shipment_id_that_comes_and_goes_keeps_the_package(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    deliveries[:] = [raw(ORDER, "amzlus", "Kettle", 2, extra_information="Ab3Cd9EfG")]
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    coordinator.async_set_icon(f"amzlus:{ORDER}@Ab3Cd9EfG", "mdi:kettle")
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    del deliveries[0]["extra_information"]
    await check(hass, config_entry)
    assert set(coordinator.data.deliveries) == {f"amzlus:{ORDER}"}
    assert coordinator.icon_for(f"amzlus:{ORDER}", "Kettle") == "mdi:kettle"

    deliveries[0]["extra_information"] = "Ab3Cd9EfG"
    await check(hass, config_entry)
    assert set(coordinator.data.deliveries) == {f"amzlus:{ORDER}@Ab3Cd9EfG"}
    assert events == []
    assert hass.states.get("sensor.parcel_kettle").state == "in_transit"


async def test_another_shipment_of_the_order_never_takes_over_a_record(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Saved by an older version for the kettle; after upgrading, only the mugs are listed."""
    hass_storage[f"{DOMAIN}.{config_entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.{config_entry.entry_id}",
        "data": {
            "initialized": True,
            "known": {
                f"amzlus:{ORDER}": {
                    "status": 0,
                    "first_seen": "2026-11-10T12:00:00+00:00",
                    "delivered_at": "2026-11-12T15:00:00+00:00",
                    "event": "Delivered||",
                    "description": "Kettle",
                    "tracking_number": ORDER,
                    "carrier_code": "amzlus",
                }
            },
        },
    }
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries[:] = [raw(ORDER, "amzlus", "Mugs", 2, extra_information="Hj7Kl2MnP")]
    await setup(hass, config_entry)
    record = config_entry.runtime_data.storage.known[f"amzlus:{ORDER}@Hj7Kl2MnP"]
    assert record["delivered_at"] is None
    assert [(e.data["type"], e.data["description"]) for e in events] == [("added", "Mugs")]

    await check_until_gone(hass, config_entry, freezer)
    assert [(e.data["type"], e.data["description"]) for e in events][1:] == [("removed", "Kettle")]


# A new add and a namesake ------------------------------------------------------


async def test_a_namesake_never_takes_the_place_of_a_new_add(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Another UPS package called "Shoes" shows up before the one just added."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(
        tracking_number="1Z999AA10000000001",
        carrier_code="ups",
        description="Shoes",
        icon="mdi:shoe-formal",
    )
    deliveries.append(raw("1Z999AA10000000002", "ups", "Shoes", 2))
    await check(hass, config_entry)
    assert "ups:1Z999AA10000000001" in coordinator.data.pending
    assert "ups:1Z999AA10000000002" not in coordinator.storage.icons


# A package listed twice --------------------------------------------------------


async def test_a_package_listed_twice_keeps_its_first_listing_and_says_so_once(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    caplog: pytest.LogCaptureFixture,
) -> None:
    deliveries.append(raw(UPS, "ups", "Grinder (gift)", 2))
    with caplog.at_level(logging.WARNING, logger="custom_components.parcel"):
        await setup(hass, config_entry)
        await check(hass, config_entry)
    assert config_entry.runtime_data.data.deliveries[UPS_KEY].description == "Coffee grinder"
    warnings = [r.getMessage() for r in caplog.records if "twice" in r.getMessage()]
    assert warnings == ["Parcel lists one UPS package twice; showing its first listing"]
    assert UPS not in warnings[0]


# Listings that can't be read whole ---------------------------------------------


def test_a_listing_without_a_number_or_carrier_is_not_a_package() -> None:
    for broken in (
        raw(None, "ups", "x", 2),  # type: ignore[arg-type]
        raw("  ", "ups", "x", 2),
        raw(UPS, None, "x", 2),  # type: ignore[arg-type]
    ):
        with pytest.raises(ValueError):
            Delivery.from_api(broken, TZ)
        assert listing_key(broken) is None
    assert listing_key("not a listing") is None
    assert listing_key(raw(ORDER, "amzlus", "x", 2, extra_information="Ab3")) == (
        f"amzlus:{ORDER}@Ab3"
    )


async def test_updates_that_are_not_a_list_count_as_none(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    await setup(hass, config_entry)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries[0]["events"] = 5
    await check(hass, config_entry)
    assert config_entry.runtime_data.data.deliveries[UPS_KEY].events == ()
    assert events == []


async def test_an_unreadable_package_stays_as_it_was_last_seen(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Listed, but not in a form that can be read: kept, however long that lasts."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    before = coordinator.data.deliveries[UPS_KEY]
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    real = Delivery.from_api

    def odd(listing: dict[str, Any], tz: Any) -> Delivery:
        if listing["tracking_number"] == UPS:
            raise TypeError("something Parcel has never sent before")
        return real(listing, tz)

    with patch.object(Delivery, "from_api", side_effect=odd):
        await check_until_gone(hass, config_entry, freezer)
    assert coordinator.data.deliveries[UPS_KEY] is before
    assert events == []


# Damaged saved state ------------------------------------------------------------


async def test_damaged_saved_state_never_stops_the_checks(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    key = f"{DOMAIN}.{config_entry.entry_id}"
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {
            "initialized": True,
            "known": {UPS_KEY: {"status": [2], "first_seen": 5, "tracking_number": UPS}},
            "pending": {"ups:1": {"tracking_number": 1, "carrier_code": "ups", "added_at": "x"}},
            "deleted": {"ups:2": "2026-02-30T10:00:00+00:00"},
            "reads": ["2026-11-16 25:00:00+00:00"],
        },
    }
    await setup(hass, config_entry)
    await check(hass, config_entry)
    coordinator = config_entry.runtime_data
    assert coordinator.last_update_success
    assert UPS_KEY in coordinator.data.deliveries
