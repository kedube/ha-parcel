"""Delivered packages stay on show until they're deleted from Parcel, as in its apps."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .conftest import check_until_gone, raw
from .test_init import setup
from custom_components.parcel.api import ParcelConnectionError, ParcelWebAuthError
from custom_components.parcel.const import (
    CONF_ACCOUNT_TOKEN,
    DELIVERED_CHECK_INTERVAL,
    DELIVERED_SENSOR_RETENTION,
    DOMAIN,
    EVENT_PACKAGE_UPDATE,
    UNLISTED_GRACE,
)
from custom_components.parcel.web_sign_in import expired_issue_id

SHOES = "9400111899223197428490"
SHOES_KEY = f"usps:{SHOES}"
ORDER = "113-4567890-1234567"


def web(number: str, carrier: str, label: str) -> dict[str, Any]:
    """One package as Parcel's web app lists it."""
    return {"tracking_number": number, "carrier_code": carrier, "label": label, "status_code": 0}


# The packages on their way in the deliveries fixture, as the web app lists them.
ON_THE_WAY = [
    web("1Z999AA10123456784", "ups", "Coffee grinder"),
    web("TBA312345678901@123-456", "amzlus", "Dog food"),
]
WITH_SHOES = [*ON_THE_WAY, web(SHOES, "usps", "Running shoes")]


def shoes(date: str = "2026-11-14 15:02:00") -> dict[str, Any]:
    """A package Parcel's API lists as delivered."""
    return raw(
        SHOES,
        "usps",
        "Running shoes",
        0,
        events=[{"event": "Delivered, In/At Mailbox", "date": date, "location": "Portland, OR"}],
    )


async def check(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    after: timedelta = timedelta(0),
) -> None:
    """Check Parcel, optionally after some time has passed."""
    freezer.tick(after)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def reload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()


def removals(events: list[Any]) -> list[tuple[str, str | None]]:
    return [(e.data["key"], e.data.get("reason")) for e in events if e.data["type"] == "removed"]


async def test_a_delivered_package_stays_after_parcels_api_stops_listing_it(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Parcel's API drops it a day after delivery; Parcel itself keeps it."""
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    assert SHOES_KEY in coordinator.data.deliveries
    assert coordinator.data.kept == {SHOES_KEY}
    assert events == []
    panel = coordinator.panel_state()
    kept = next(item for item in panel["deliveries"] if item["key"] == SHOES_KEY)
    assert kept["status"] == "delivered"
    assert kept["events"][0]["location"] == "Portland, OR"
    assert kept["delivered_at"] is not None


async def test_a_kept_package_goes_once_it_is_deleted_from_parcel(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Two reads of the web app's list must leave it out, so one bad reply loses nothing."""
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    coordinator.storage.icons[SHOES_KEY] = "mdi:shoe-sneaker"
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    mock_parcel.web_list.return_value = ON_THE_WAY  # deleted in the Parcel app
    await check(hass, config_entry, freezer, DELIVERED_CHECK_INTERVAL)
    assert SHOES_KEY in coordinator.data.deliveries
    await check(hass, config_entry, freezer, UNLISTED_GRACE)
    assert SHOES_KEY not in coordinator.data.deliveries
    assert coordinator.data.kept == set()
    assert removals(events) == [(SHOES_KEY, "deleted")]
    assert events[0].data["message"] == "Running shoes is no longer tracked"
    storage = coordinator.storage
    assert SHOES_KEY not in storage.delivered
    assert SHOES_KEY not in storage.known
    assert SHOES_KEY not in storage.icons
    assert SHOES_KEY not in storage.unlisted


async def test_one_read_that_leaves_it_out_is_not_enough(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)

    mock_parcel.web_list.return_value = ON_THE_WAY
    await check(hass, config_entry, freezer, DELIVERED_CHECK_INTERVAL)
    mock_parcel.web_list.return_value = WITH_SHOES
    await check(hass, config_entry, freezer, UNLISTED_GRACE)
    mock_parcel.web_list.return_value = ON_THE_WAY
    await check(hass, config_entry, freezer, UNLISTED_GRACE)
    # Left out twice, but not twice in a row.
    assert SHOES_KEY in coordinator.data.deliveries


async def test_a_package_deleted_in_the_app_right_after_delivery_still_goes(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """When Parcel's API stops listing a package, the web app's list is read right away."""
    lamp = raw("776598765432", "fedex", "Desk lamp", 0)
    deliveries.extend([lamp, shoes()])
    mock_parcel.web_list.return_value = [*WITH_SHOES, web("776598765432", "fedex", "Desk lamp")]
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    # The lamp is kept, so the hourly reads have started.
    deliveries.remove(lamp)
    await check_until_gone(hass, config_entry, freezer)
    read_at = coordinator.storage.delivered_checked_at
    await check(hass, config_entry, freezer, timedelta(minutes=20))
    assert coordinator.storage.delivered_checked_at == read_at
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    deliveries.pop()
    mock_parcel.web_list.return_value = [*ON_THE_WAY, web("776598765432", "fedex", "Desk lamp")]
    await check(hass, config_entry, freezer, timedelta(minutes=5))
    assert coordinator.storage.delivered_checked_at != read_at
    await check(hass, config_entry, freezer, UNLISTED_GRACE)
    assert SHOES_KEY not in coordinator.data.deliveries
    assert coordinator.data.kept == {"fedex:776598765432"}
    assert removals(events) == [(SHOES_KEY, "deleted")]


async def test_the_web_list_is_read_hourly_not_at_every_check(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    deliveries.pop()
    await check(hass, config_entry, freezer)
    first = coordinator.storage.delivered_checked_at
    assert first is not None

    for _ in range(3):
        await check(hass, config_entry, freezer, timedelta(minutes=10))
    assert coordinator.storage.delivered_checked_at == first
    await check(hass, config_entry, freezer, timedelta(minutes=30))
    assert coordinator.storage.delivered_checked_at == first + timedelta(minutes=60)


async def test_a_web_list_without_the_packages_on_their_way_changes_nothing(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """It isn't this account's whole list (another account's, or cut short)."""
    deliveries.append(shoes())
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.return_value = []
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    for _ in range(3):
        await check(hass, config_entry, freezer, DELIVERED_CHECK_INTERVAL)
    assert SHOES_KEY in coordinator.data.deliveries


async def test_a_web_list_that_cannot_be_read_changes_nothing(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Nor does an expired sign-in, which is reported as usual; checks carry on."""
    deliveries.append(shoes())
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = ParcelConnectionError("down")
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    assert coordinator.last_update_success
    assert SHOES_KEY in coordinator.data.deliveries

    mock_parcel.web_list.side_effect = ParcelWebAuthError("expired")
    await check(hass, config_entry, freezer, DELIVERED_CHECK_INTERVAL)
    assert coordinator.last_update_success
    assert SHOES_KEY in coordinator.data.deliveries
    assert ir.async_get(hass).async_get_issue(DOMAIN, expired_issue_id(config_entry.entry_id))


async def test_without_a_web_sign_in_delivered_packages_go_with_parcels_list(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Only the web app's list can tell deleted from no longer listed."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Parcel", data={"api_key": "test-key"}, options={"scan_interval": 5}
    )
    deliveries.append(shoes())
    await setup(hass, entry)
    coordinator = entry.runtime_data
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    deliveries.pop()
    await check_until_gone(hass, entry, freezer)
    assert SHOES_KEY not in coordinator.data.deliveries
    assert coordinator.storage.delivered == {}
    assert removals(events) == [(SHOES_KEY, "no_longer_listed")]
    mock_parcel.web_list.assert_not_awaited()


async def test_removing_the_web_sign_in_lets_kept_packages_go_quietly(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """They weren't deleted, so nothing announces that they were."""
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    options = {k: v for k, v in config_entry.options.items() if k != CONF_ACCOUNT_TOKEN}
    hass.config_entries.async_update_entry(config_entry, options=options)
    await reload(hass, config_entry)
    coordinator = config_entry.runtime_data
    assert SHOES_KEY not in coordinator.data.deliveries
    assert coordinator.storage.delivered == {}
    assert SHOES_KEY not in coordinator.storage.known
    await check(hass, config_entry, freezer, timedelta(minutes=5))
    assert events == []


async def test_kept_packages_survive_a_restart(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    await reload(hass, config_entry)
    coordinator = config_entry.runtime_data
    assert coordinator.data.kept == {SHOES_KEY}
    await check(hass, config_entry, freezer, timedelta(minutes=5))
    assert SHOES_KEY in coordinator.data.deliveries
    assert events == []


async def test_a_kept_package_can_be_deleted_from_home_assistant(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    deliveries.append(shoes())
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)

    mock_parcel.web_list.side_effect = [WITH_SHOES, ON_THE_WAY]
    await coordinator.async_delete_package(SHOES_KEY)
    mock_parcel.web_delete.assert_awaited_once_with(SHOES, "usps")
    assert SHOES_KEY not in coordinator.data.deliveries
    assert coordinator.storage.delivered == {}

    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = ON_THE_WAY
    await check(hass, config_entry, freezer, DELIVERED_CHECK_INTERVAL)
    assert SHOES_KEY not in coordinator.data.deliveries


async def test_a_package_deleted_while_parcel_still_lists_it_is_not_kept(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Parcel's API lists it a while longer; it stays hidden, and isn't kept afterwards."""
    deliveries.append(shoes())
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = [WITH_SHOES, ON_THE_WAY]
    await coordinator.async_delete_package(SHOES_KEY)
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = ON_THE_WAY

    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    await check(hass, config_entry, freezer, timedelta(minutes=5))
    assert SHOES_KEY not in coordinator.data.deliveries
    deliveries.pop()
    for _ in range(3):
        await check(hass, config_entry, freezer, timedelta(minutes=5))
        assert SHOES_KEY not in coordinator.data.deliveries
    assert coordinator.storage.delivered == {}
    assert events == []


async def test_a_kept_package_without_a_delivery_time_loses_its_sensor_after_two_days(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Counted from when it was first seen, so the sensor doesn't stay for good."""
    deliveries.append(shoes(date="--//--"))
    mock_parcel.web_list.return_value = WITH_SHOES
    await setup(hass, config_entry)
    assert hass.states.get("sensor.parcel_running_shoes") is not None
    deliveries.pop()
    await check_until_gone(hass, config_entry, freezer)
    assert hass.states.get("sensor.parcel_running_shoes") is not None

    await check(hass, config_entry, freezer, DELIVERED_SENSOR_RETENTION)
    assert SHOES_KEY in config_entry.runtime_data.data.deliveries
    assert hass.states.get("sensor.parcel_running_shoes") is None


async def test_a_kept_shipment_is_not_taken_over_by_another_of_the_same_order(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Amazon shipments share the order number, and often the name too."""
    first = f"amzlus:{ORDER}@Ab3Cd9EfG"
    second = f"amzlus:{ORDER}@Hj7Kl2MnP"
    deliveries.append(raw(ORDER, "amzlus", "Amazon order", 0, extra_information="Ab3Cd9EfG"))
    mock_parcel.web_list.return_value = [
        *ON_THE_WAY,
        web(f"{ORDER}@Ab3Cd9EfG", "amzlus", "Amazon order"),
        web(f"{ORDER}@Hj7Kl2MnP", "amzlus", "Amazon order"),
    ]
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)

    deliveries[-1] = raw(ORDER, "amzlus", "Amazon order", 2, extra_information="Hj7Kl2MnP")
    await check_until_gone(hass, config_entry, freezer)
    assert coordinator.data.kept == {first}
    assert coordinator.data.deliveries[second].status == "in_transit"
    assert [(e.data["type"], e.data["key"]) for e in events] == [("added", second)]
