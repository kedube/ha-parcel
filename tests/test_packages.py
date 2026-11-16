"""Adding, deleting and following packages: the cases that once went wrong."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import issue_registry as ir

from .conftest import raw
from .test_init import setup
from custom_components.parcel.api import ParcelConnectionError
from custom_components.parcel.const import DOMAIN, EVENT_PACKAGE_UPDATE
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
) -> None:
    """Added again in the Parcel app later, the package appears like any new one."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.web_list.side_effect = [[STORED_UPS], []]
    await coordinator.async_delete_package(UPS_KEY)
    assert UPS_KEY in coordinator.storage.deleted

    grinder = deliveries.pop(0)
    await coordinator.async_refresh()
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
        "tracking_number": "450436033378735815683",
        "carrier_code": "pholder",
        "label": "Birthday gift",
        "date_added": "2026-11-16 10:00:00",
    }
    mock_parcel.web_list.side_effect = [[stored], []]
    await coordinator.async_delete_package("pholder:HATEST1")
    mock_parcel.web_delete.assert_awaited_once_with("450436033378735815683", "pholder")
    assert coordinator.data.pending == {}


async def test_a_new_add_is_not_confused_with_a_listed_namesake(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Deleting a just-added placeholder never takes an older package of the same name."""
    deliveries.append(raw("450436033378735815683", "pholder", "Birthday gift", 1))
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(
        tracking_number="HATEST2", carrier_code="pholder", description="Birthday gift"
    )
    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = [
        {
            "tracking_number": "450436033378735815683",
            "carrier_code": "pholder",
            "label": "Birthday gift",
        }
    ]
    await coordinator.async_delete_package("pholder:HATEST2")
    mock_parcel.web_delete.assert_not_awaited()
    assert "pholder:450436033378735815683" in coordinator.data.deliveries
    assert coordinator.data.pending == {}


# Icons -----------------------------------------------------------------------


async def test_an_icon_choice_goes_when_its_package_does(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    coordinator.async_set_icon(UPS_KEY, "mdi:gift")
    assert coordinator.icon_for(UPS_KEY, "Coffee grinder") == "mdi:gift"
    await coordinator.async_refresh()
    assert coordinator.storage.icons == {UPS_KEY: "mdi:gift"}

    deliveries.pop(0)
    await coordinator.async_refresh()
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
    assert day.attributes["package"] == "Purina Pro Plan Small Breed"
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
