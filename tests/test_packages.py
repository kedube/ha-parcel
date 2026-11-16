"""Adding, deleting and following packages: the cases that once went wrong."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from .conftest import check_until_gone, raw
from .test_init import setup
from custom_components.parcel.api import ParcelConnectionError
from custom_components.parcel.const import CONF_PACKAGE_ID_SECRET, DOMAIN, EVENT_PACKAGE_UPDATE
from custom_components.parcel.entity import package_id
from custom_components.parcel.sensor import ParcelSummarySensor
from custom_components.parcel.summary import build_summary
from custom_components.parcel.web_sign_in import expired_issue_id, expiring_issue_id

UPS = "1Z999AA10123456784"
UPS_KEY = f"ups:{UPS}"
STORED_UPS = {"tracking_number": UPS, "carrier_code": "ups", "label": "Coffee grinder"}


# Deleting, then wanting it back ----------------------------------------------


async def test_a_deleted_package_can_be_added_again(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Re-adding clears the delete marker, so Parcel's listing shows up straight away."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = [[STORED_UPS], []]
    await coordinator.async_delete_package(UPS_KEY)
    # Parcel's cached list still shows it for a while; it stays hidden.
    await coordinator.async_refresh()
    assert UPS_KEY not in coordinator.data.deliveries

    await coordinator.async_add_package(tracking_number=UPS, description="Coffee grinder (again)")
    deliveries[0]["description"] = "Coffee grinder (again)"
    await coordinator.async_refresh()
    assert coordinator.data.deliveries[UPS_KEY].description == "Coffee grinder (again)"
    assert coordinator.data.pending == {}
    assert coordinator.storage.deleted == {}


async def test_the_delete_marker_goes_once_parcel_stops_listing(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Added again in the Parcel app later, the package appears like any new one."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = [[STORED_UPS], []]
    await coordinator.async_delete_package(UPS_KEY)
    assert UPS_KEY in coordinator.storage.deleted
    mock_parcel.web_list.side_effect = None  # the sign-in check runs as time passes

    grinder = deliveries.pop(0)
    # One reply without it isn't enough: Parcel's next one may list it again.
    await coordinator.async_refresh()
    assert UPS_KEY in coordinator.storage.deleted
    await check_until_gone(hass, config_entry, freezer)
    assert coordinator.storage.deleted == {}

    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries.append(grinder)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert UPS_KEY in coordinator.data.deliveries
    assert [event.data["type"] for event in events] == ["added"]


# One package, however its number is typed ------------------------------------


@pytest.mark.parametrize("typed", [UPS.lower(), "1Z 999 AA1 01 2345 6784", "1z999-aa1-0123456784"])
async def test_the_same_number_in_another_format_is_already_tracked(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry, typed: str
) -> None:
    """No add is spent on a package that is already there."""
    await setup(hass, config_entry)
    with pytest.raises(ServiceValidationError) as raised:
        await config_entry.runtime_data.async_add_package(
            tracking_number=typed, description="Again"
        )
    assert raised.value.translation_key == "already_tracking"
    mock_parcel.add.assert_not_awaited()


async def test_a_pending_add_is_also_a_duplicate(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(tracking_number="1Z999AA10123456799", description="Lamp")
    with pytest.raises(ServiceValidationError):
        await coordinator.async_add_package(
            tracking_number="1z999aa10123456799", description="Lamp"
        )
    assert mock_parcel.add.await_count == 1


async def test_a_double_submit_spends_one_add(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Two requests for the same package at the same moment: the second is refused."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    release = asyncio.Event()

    async def slow_add(**_kwargs: object) -> None:
        await release.wait()

    mock_parcel.add.side_effect = slow_add
    first = hass.async_create_task(
        coordinator.async_add_package(tracking_number="1Z999AA10123456799", description="Lamp")
    )
    await asyncio.sleep(0)
    with pytest.raises(ServiceValidationError):
        await coordinator.async_add_package(
            tracking_number="1z999aa10123456799", description="Lamp"
        )
    release.set()
    await first
    assert mock_parcel.add.await_count == 1
    assert list(coordinator.data.pending) == ["ups:1Z999AA10123456799"]
    assert coordinator.panel_state()["adds_left"] == 19


@pytest.mark.parametrize("typed", [UPS.lower(), "1Z 999 AA1 01 2345 6784"])
async def test_the_delete_action_finds_any_format(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry, typed: str
) -> None:
    await setup(hass, config_entry)
    mock_parcel.web_list.side_effect = [[STORED_UPS], []]
    await hass.services.async_call(
        DOMAIN, "delete_package", {"tracking_number": typed}, blocking=True
    )
    mock_parcel.web_delete.assert_awaited_once_with(UPS, "ups")


async def test_the_delete_action_says_when_nothing_matches(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    with pytest.raises(ServiceValidationError) as raised:
        await hass.services.async_call(
            DOMAIN, "delete_package", {"tracking_number": "NOPE"}, blocking=True
        )
    assert raised.value.translation_key == "package_not_found"
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "delete_package", {"tracking_number": UPS, "carrier": "fedex"}, blocking=True
        )


# Deleting only what was asked for --------------------------------------------


async def test_deleting_never_removes_a_namesake(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Already gone from Parcel: the other package with the same name is left alone."""
    deliveries.append(raw("TBA000000000001", "amzlus", "Amazon", 2))
    deliveries.append(raw("TBA000000000002", "amzlus", "Amazon", 2))
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    # It was deleted in the Parcel app a moment ago, so the web list no longer has it.
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = [
        {"tracking_number": "TBA000000000002", "carrier_code": "amzlus", "label": "Amazon"}
    ]
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    await coordinator.async_delete_package("amzlus:TBA000000000001")
    await hass.async_block_till_done()

    mock_parcel.web_delete.assert_not_awaited()
    assert "amzlus:TBA000000000001" not in coordinator.data.deliveries
    assert "amzlus:TBA000000000002" in coordinator.data.deliveries
    assert [(e.data["type"], e.data["reason"]) for e in events] == [("removed", "deleted")]


async def test_deleting_a_placeholder_before_parcel_lists_it(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Parcel stores its own number for a placeholder; its name finds it."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(
        tracking_number="HATEST1", carrier_code="pholder", description="Birthday gift"
    )
    stored = {
        "tracking_number": "450000000000000000001",
        "carrier_code": "pholder",
        "label": "Birthday gift",
        "date_added": "2026-11-16 10:00:00",
    }
    mock_parcel.web_list.side_effect = [[stored], []]
    await coordinator.async_delete_package("pholder:HATEST1")
    mock_parcel.web_delete.assert_awaited_once_with("450000000000000000001", "pholder")
    assert coordinator.data.pending == {}


async def test_a_new_add_is_not_confused_with_a_listed_namesake(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Deleting a just-added placeholder never takes an older package of the same name.

    Until Parcel has stored the new one, there is nothing to delete, and it says so
    instead of hiding a package that is about to show up in Parcel.
    """
    deliveries.append(raw("450000000000000000001", "pholder", "Birthday gift", 1))
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(
        tracking_number="HATEST2", carrier_code="pholder", description="Birthday gift"
    )
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = [
        {
            "tracking_number": "450000000000000000001",
            "carrier_code": "pholder",
            "label": "Birthday gift",
        },
        {"tracking_number": "1Z999AA10123456784", "carrier_code": "ups", "label": "Grinder"},
    ]
    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_delete_package("pholder:HATEST2")
    assert raised.value.translation_key == "delete_not_added_yet"
    mock_parcel.web_delete.assert_not_awaited()
    assert "pholder:450000000000000000001" in coordinator.data.deliveries
    assert "pholder:HATEST2" in coordinator.data.pending


async def test_a_sign_in_for_another_account_deletes_nothing(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Its list doesn't have the package, but that doesn't mean it was deleted."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = [
        {"tracking_number": "9400111202555842332669", "carrier_code": "usps", "label": "Socks"}
    ]
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_delete_package("ups:1Z999AA10123456784")
    await hass.async_block_till_done()
    assert raised.value.translation_key == "web_sign_in_other_account"
    mock_parcel.web_delete.assert_not_awaited()
    assert "ups:1Z999AA10123456784" in coordinator.data.deliveries
    assert events == []


ORDER = "113-4567890-1234567"  # an Amazon order as Parcel's API gives it
STORED_ORDER = f"{ORDER}@Ab3Cd9EfG"  # and as its web app holds it


async def test_an_amazon_order_is_deleted_under_the_web_apps_number(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """The only package on its way; it was once taken as deleted elsewhere and hidden."""
    deliveries[:] = [raw(ORDER, "amzlus", "Kettle", 4, extra_information="Ab3Cd9EfG")]
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    stored = {"tracking_number": STORED_ORDER, "carrier_code": "amzlus", "label": "Kettle"}
    mock_parcel.web_list.side_effect = [[stored], []]
    # Its key carries the shipment ID, as the web app's number does.
    await coordinator.async_delete_package(f"amzlus:{STORED_ORDER}")
    mock_parcel.web_delete.assert_awaited_once_with(STORED_ORDER, "amzlus")
    assert f"amzlus:{STORED_ORDER}" not in coordinator.data.deliveries


async def test_a_number_parcel_lists_ambiguously_is_neither_deleted_nor_hidden(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Two shipments of one order, and nothing to say which one this is."""
    deliveries[:] = [raw(ORDER, "amzlus", "Kettle", 4)]
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = [
        {"tracking_number": STORED_ORDER, "carrier_code": "amzlus", "label": "Kettle"},
        {"tracking_number": f"{ORDER}@Hj7Kl2MnP", "carrier_code": "amzlus", "label": "Mugs"},
    ]
    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_delete_package(f"amzlus:{ORDER}")
    assert raised.value.translation_key == "delete_ambiguous"
    mock_parcel.web_delete.assert_not_awaited()
    assert f"amzlus:{ORDER}" in coordinator.data.deliveries


async def test_a_check_landing_mid_delete_does_not_bring_the_package_back(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """A scheduled check that finishes while Parcel's web app answers replaces the data."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    stored = {"tracking_number": UPS, "carrier_code": "ups", "label": "Coffee grinder"}
    mock_parcel.web_list.side_effect = [[stored], []]

    async def check_lands_meanwhile(*_args: object) -> None:
        await coordinator.async_refresh()

    mock_parcel.web_delete.side_effect = check_lands_meanwhile
    await coordinator.async_delete_package(UPS_KEY)
    await hass.async_block_till_done()
    assert UPS_KEY not in coordinator.data.deliveries
    assert hass.states.get("sensor.parcel_coffee_grinder") is None


def shipment(name: str, shipment_id: str, status: int = 2) -> dict:
    """One shipment of the order, as Parcel's API lists it."""
    return raw(
        ORDER,
        "amzlus",
        name,
        status,
        extra_information=shipment_id,
        events=[{"event": "Shipped", "date": "2026-11-15 08:00:00"}],
    )


async def test_each_shipment_of_an_amazon_order_is_tracked(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Two parts of one order share its number; they once collapsed into one."""
    deliveries[:] = [shipment("Kettle", "Ab3Cd9EfG"), shipment("Mugs", "Hj7Kl2MnP", 4)]
    await setup(hass, config_entry)
    assert set(config_entry.runtime_data.data.deliveries) == {
        f"amzlus:{ORDER}@Ab3Cd9EfG",
        f"amzlus:{ORDER}@Hj7Kl2MnP",
    }
    assert hass.states.get("sensor.parcel_kettle").state == "in_transit"
    assert hass.states.get("sensor.parcel_mugs").state == "out_for_delivery"
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"


async def test_the_delete_action_needs_to_know_which_shipment(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    deliveries[:] = [shipment("Kettle", "Ab3Cd9EfG"), shipment("Mugs", "Hj7Kl2MnP")]
    await setup(hass, config_entry)
    with pytest.raises(ServiceValidationError) as raised:
        await hass.services.async_call(
            DOMAIN, "delete_package", {"tracking_number": ORDER}, blocking=True
        )
    assert raised.value.translation_key == "choose_shipment"
    mugs = f"{ORDER}@Hj7Kl2MnP"
    stored = {"tracking_number": mugs, "carrier_code": "amzlus", "label": "Mugs"}
    mock_parcel.web_list.side_effect = [[stored], []]
    await hass.services.async_call(
        DOMAIN, "delete_package", {"tracking_number": mugs}, blocking=True
    )
    mock_parcel.web_delete.assert_awaited_once_with(mugs, "amzlus")


async def test_upgrading_keeps_an_amazon_shipment_as_it_was(
    hass: HomeAssistant,
    hass_storage: dict,
    mock_parcel: SimpleNamespace,
    deliveries: list,
) -> None:
    """Saved under "amzlus:<order number>" by an older version: no removed/added events,
    the icon chosen for it stays, and so does its sensor's entity ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Parcel",
        data={"api_key": "test-key", CONF_PACKAGE_ID_SECRET: "a" * 32},
        options={"scan_interval": 5, "package_sensors": True},
        minor_version=2,
    )
    old_key = f"amzlus:{ORDER}"
    hass_storage[f"parcel.{entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"parcel.{entry.entry_id}",
        "data": {
            "initialized": True,
            "known": {
                old_key: {
                    "status": 2,
                    "first_seen": "2026-11-14T12:00:00+00:00",
                    "delivered_at": None,
                    "event": "Shipped|2026-11-15 08:00:00|",
                    "description": "Kettle",
                    "tracking_number": ORDER,
                    "carrier_code": "amzlus",
                }
            },
            "icons": {old_key: "mdi:kettle"},
        },
    }
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_package_{package_id(entry, old_key)}",
        config_entry=entry,
        suggested_object_id="parcel_kettle",
    )
    deliveries[:] = [shipment("Kettle", "Ab3Cd9EfG")]
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    new_key = f"amzlus:{ORDER}@Ab3Cd9EfG"
    assert events == []
    assert coordinator.storage.known[new_key]["first_seen"] == "2026-11-14T12:00:00+00:00"
    assert coordinator.icon_for(new_key, "Kettle") == "mdi:kettle"
    assert hass.states.get("sensor.parcel_kettle").state == "in_transit"
    assert hass.states.get("sensor.parcel_kettle_2") is None


async def test_deleting_an_add_never_takes_an_older_namesake(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Only placeholders are looked up by name: last year's "Running shoes" is left alone."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(
        tracking_number="1Z999AA10000000001", carrier_code="ups", description="Running shoes"
    )
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = [
        {"tracking_number": "1Z999AA10123456784", "carrier_code": "ups", "label": "Grinder"},
        {
            "tracking_number": "1Z999AA19999999999",
            "carrier_code": "ups",
            "label": "Running shoes",
            "date_added": "2025-03-01 09:00:00",
        },
    ]
    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_delete_package("ups:1Z999AA10000000001")
    assert raised.value.translation_key == "delete_not_added_yet"
    mock_parcel.web_delete.assert_not_awaited()
    assert "ups:1Z999AA10000000001" in coordinator.data.pending


async def test_one_odd_package_does_not_take_the_others_down(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Placeholder dates, impossible values and missing fields cost only that package."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    deliveries += [
        raw("9400111202555842332669", "usps", "Running shoes", 2, timestamp_expected=253402300799),
        raw("9400111202555842332670", "usps", "Rain boots", float("inf")),
        raw("9400111202555842332671", "usps", "Hat", 2, date_expected="0001-01-01T00:00:00+05:00"),
        {"carrier_code": "usps", "description": "No number"},
    ]
    await setup(hass, config_entry)
    assert config_entry.runtime_data.last_update_success
    assert hass.states.get("sensor.parcel_on_the_way").state == "5"
    assert hass.states.get("sensor.parcel_running_shoes").state == "in_transit"
    assert hass.states.get("sensor.parcel_rain_boots").state == "not_found"


# Icons -----------------------------------------------------------------------


async def test_one_impossible_carrier_date_does_not_drop_the_package(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """It used to vanish, with a "removed" event, until the carrier corrected the date."""
    await setup(hass, config_entry)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries[0]["events"].insert(0, {"event": "Arrived", "date": "2026-02-30 10:00:00"})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert UPS_KEY in config_entry.runtime_data.data.deliveries
    assert [event.data["type"] for event in events] == ["update"]


async def test_an_icon_choice_goes_when_its_package_does(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    coordinator.async_set_icon(UPS_KEY, "mdi:gift")
    assert coordinator.icon_for(UPS_KEY, "Coffee grinder") == "mdi:gift"
    await coordinator.async_refresh()
    assert coordinator.storage.icons == {UPS_KEY: "mdi:gift"}

    deliveries.pop(0)
    await coordinator.async_refresh()
    assert coordinator.storage.icons == {UPS_KEY: "mdi:gift"}  # not gone yet
    await check_until_gone(hass, config_entry, freezer)
    assert coordinator.storage.icons == {}


async def test_an_icon_needs_a_package(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    with pytest.raises(ServiceValidationError):
        coordinator.async_set_icon("ups:NO-SUCH-PACKAGE", "mdi:gift")
    assert coordinator.storage.icons == {}
    # A pending add can have one, and it survives the checks while it waits.
    await coordinator.async_add_package(tracking_number="1Z999AA10123456799", description="Lamp")
    coordinator.async_set_icon("ups:1Z999AA10123456799", "mdi:desk-lamp")
    await coordinator.async_refresh()
    assert coordinator.storage.icons == {"ups:1Z999AA10123456799": "mdi:desk-lamp"}


# The extra detail some carriers need ----------------------------------------


async def test_the_extra_detail_goes_in_the_field_the_carrier_needs(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Email for Apple orders, postcode for Yodel, whichever way it was passed."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data

    # The action: both given, each goes in its own field.
    await hass.services.async_call(
        DOMAIN,
        "add_package",
        {
            "tracking_number": "W1234567890",
            "description": "Phone",
            "postcode": "90210",
            "email": "me@example.com",
        },
        blocking=True,
    )
    sent = mock_parcel.add.call_args.kwargs
    assert sent["carrier_code"] == "apple"
    assert sent["email"] == "me@example.com"
    assert sent["postcode"] == "90210"

    # The panel sends one "extra" value; the carrier decides what it is.
    await coordinator.async_add_package(
        tracking_number="W1234567891", description="Watch", extra=" me@example.com "
    )
    sent = mock_parcel.add.call_args.kwargs
    assert (sent["email"], sent["postcode"]) == ("me@example.com", None)

    await coordinator.async_add_package(
        tracking_number="JD0002251234", carrier_code="yodel", description="Shoes", extra="AB1 2CD"
    )
    sent = mock_parcel.add.call_args.kwargs
    assert (sent["email"], sent["postcode"]) == (None, "AB1 2CD")


async def test_the_wrong_detail_is_refused_before_an_add_is_spent(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """A postcode can't stand in for the email an Apple order needs."""
    await setup(hass, config_entry)
    with pytest.raises(ServiceValidationError) as raised:
        await hass.services.async_call(
            DOMAIN,
            "add_package",
            {"tracking_number": "W1234567890", "description": "Phone", "postcode": "90210"},
            blocking=True,
        )
    assert raised.value.translation_key == "extra_required"
    mock_parcel.add.assert_not_awaited()


# Sensors ---------------------------------------------------------------------


async def test_a_package_sensor_follows_a_rename(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    await setup(hass, config_entry)
    assert (
        hass.states.get("sensor.parcel_coffee_grinder").attributes["friendly_name"]
        == "Parcel Coffee grinder"
    )
    deliveries[0]["description"] = "Espresso machine"
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.parcel_coffee_grinder")
    assert state.attributes["friendly_name"] == "Parcel Espresso machine"
    assert state.attributes["description"] == "Espresso machine"


async def test_next_delivery_separates_the_day_from_the_time(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A day-only estimate fills the day sensor and never shows up as midnight."""
    freezer.move_to("2026-11-16 04:48:00+00:00")  # late evening on the 15th, US Pacific
    await hass.config.async_set_time_zone("America/Los_Angeles")
    grinder = deliveries[0]
    del grinder["date_expected"], grinder["date_expected_end"]
    await setup(hass, config_entry)

    # Only the dog food has an estimate, and it is a day without a time.
    day = hass.states.get("sensor.parcel_next_delivery_day")
    assert day.state == "2026-11-16"
    assert day.attributes["package"] == "Dog food"
    assert day.attributes["count"] == 1
    when = hass.states.get("sensor.parcel_next_delivery")
    assert when.state == "unknown"
    assert when.attributes["package"] is None

    # The carrier gives the grinder a window on the 17th.
    grinder["date_expected"] = "2026-11-17 13:00:00"
    grinder["date_expected_end"] = "2026-11-17 16:00:00"
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.parcel_next_delivery_day").state == "2026-11-16"
    when = hass.states.get("sensor.parcel_next_delivery")
    assert when.state == "2026-11-17T21:00:00+00:00"
    assert when.attributes["package"] == "Coffee grinder"
    assert when.attributes["window_end"] == "2026-11-17T16:00:00-08:00"
    assert "date_only" not in when.attributes


async def test_the_summary_is_worked_out_once_per_change(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Eight sensors read it; it's computed once, and history skips the package list."""
    await setup(hass, config_entry)
    with patch("custom_components.parcel.coordinator.build_summary", wraps=build_summary) as built:
        await config_entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
    assert built.call_count == 1
    assert "packages" in hass.states.get("sensor.parcel_on_the_way").attributes
    assert ParcelSummarySensor._unrecorded_attributes == frozenset({"packages"})


# When Parcel can't be reached ------------------------------------------------


async def test_a_short_outage_keeps_the_last_known_packages(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Sensors don't flip to unavailable (and re-trigger automations) for a blip."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.get.side_effect = ParcelConnectionError("Couldn't reach Parcel: timed out")

    freezer.tick(timedelta(minutes=5))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"
    assert coordinator.panel_state()["last_error"] == "Couldn't reach Parcel: timed out"

    # Asking by hand says the check failed, instead of "up to date".
    freezer.tick(timedelta(minutes=5))
    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_manual_refresh()
    assert raised.value.translation_placeholders == {"error": "Couldn't reach Parcel: timed out"}

    # Half an hour on it is a real outage, and the sensors say so.
    freezer.tick(timedelta(minutes=25))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.parcel_on_the_way").state == "unavailable"

    # Back again.
    mock_parcel.get.side_effect = None
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"
    assert coordinator.panel_state()["last_error"] is None
    assert coordinator.last_error is None


# Removing the account --------------------------------------------------------


async def test_removing_the_account_clears_its_repairs(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    config_entry.runtime_data.web_sign_in.async_mark_expired()
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, expired_issue_id(config_entry.entry_id))
    with patch("custom_components.parcel.async_unregister_panel"):
        assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, expired_issue_id(config_entry.entry_id)) is None
    assert issues.async_get_issue(DOMAIN, expiring_issue_id(config_entry.entry_id)) is None
