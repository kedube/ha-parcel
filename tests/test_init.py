"""Setting up an account, entities, events, limits, add and delete."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .conftest import raw
from custom_components.parcel.api import ParcelAuthError, ParcelRequestError, ParcelWebAuthError
from custom_components.parcel.const import DOMAIN, EVENT_PACKAGE_UPDATE, READS_PER_HOUR
from custom_components.parcel.device_trigger import async_get_triggers


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_summary_and_package_sensors(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Summary sensors carry counts and sentences; each package gets a sensor."""
    await setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    on_the_way = hass.states.get("sensor.parcel_on_the_way")
    assert on_the_way.state == "2"
    assert on_the_way.attributes["message"] == "2 packages are on the way"
    assert hass.states.get("sensor.parcel_needs_attention").state == "0"

    grinder = hass.states.get("sensor.parcel_coffee_grinder")
    assert grinder.state == "in_transit"
    assert grinder.attributes["icon"] == "mdi:coffee"
    dog_food = hass.states.get("sensor.parcel_dog_food")
    assert dog_food.attributes["icon"] == "mdi:paw"
    assert dog_food.attributes["expected"] == "2026-11-16"
    assert hass.states.get("event.parcel_package_update") is not None
    assert hass.states.get("button.parcel_check_for_updates") is not None


async def test_status_change_fires_events_and_device_triggers(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """A package going out for delivery fires the bus event and updates the event entity."""
    await setup(hass, config_entry)
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    deliveries[0]["status_code"] = 4
    deliveries.append(raw("9400111202555842332669", "usps", "Running shoes", 2))
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    types = sorted(event.data["type"] for event in events)
    assert types == ["added", "out_for_delivery"]
    out = next(event for event in events if event.data["type"] == "out_for_delivery")
    assert out.data["message"] == "Coffee grinder is out for delivery"
    assert out.data["previous_status"] == "in_transit"
    device = dr.async_get(hass).async_get(config_entry.runtime_data.device_id)
    assert (DOMAIN, config_entry.entry_id) in device.identifiers
    assert out.data["device_id"] == device.id
    assert hass.states.get("sensor.parcel_out_for_delivery").state == "1"
    assert hass.states.get("event.parcel_package_update").attributes["event_type"] in {
        "added",
        "out_for_delivery",
    }

    triggers = await async_get_triggers(hass, device.id)
    assert {trigger["type"] for trigger in triggers} >= {
        "package_delivered",
        "package_out_for_delivery",
    }


async def test_first_load_does_not_announce_existing_packages(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Packages already in Parcel at setup don't fire 'added'."""
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    await setup(hass, config_entry)
    assert events == []


async def test_bad_api_key_starts_reauth(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """A revoked key asks for a new one instead of failing silently."""
    mock_parcel.get.side_effect = ParcelAuthError("Account not found")
    config_entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(
        flow["context"]["source"] == "reauth" for flow in hass.config_entries.flow.async_progress()
    )


async def test_manual_refresh_keeps_reads_for_schedule(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Manual checks stop before Parcel's hourly limit is used up."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    from homeassistant.util import dt as dt_util

    now = dt_util.utcnow()
    for _ in range(READS_PER_HOUR):
        coordinator.storage.record_read(now)
    coordinator.data.fetched_at = None
    with pytest.raises(HomeAssistantError):
        await coordinator.async_manual_refresh()


async def test_add_package_goes_pending_then_matches(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Adding detects the carrier, shows as pending, and matches when Parcel lists it."""
    await setup(hass, config_entry)
    response = await hass.services.async_call(
        DOMAIN,
        "add_package",
        {"tracking_number": "1Z 999 AA1 01 2345 6799", "description": "Desk lamp"},
        blocking=True,
        return_response=True,
    )
    assert response["carrier"] == "ups"
    kwargs = mock_parcel.add.call_args.kwargs
    assert kwargs["tracking_number"] == "1Z999AA10123456799"
    assert kwargs["carrier_code"] == "ups"
    coordinator = config_entry.runtime_data
    assert "ups:1Z999AA10123456799" in coordinator.data.pending
    assert coordinator.panel_state()["adds_left"] == 19

    deliveries.append(raw("1Z999AA10123456799", "ups", "Desk lamp", 8))
    await coordinator.async_refresh()
    assert coordinator.data.pending == {}
    assert "ups:1Z999AA10123456799" in coordinator.data.deliveries


async def test_placeholder_pending_matches_by_name(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Parcel generates its own number for placeholders; the pending add still resolves."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_add_package(
        tracking_number="HATEST1",
        carrier_code="pholder",
        description="Test placeholder",
        icon="mdi:gift",
    )
    deliveries.append(raw("450000000000000000001", "pholder", "Test placeholder", 1))
    await coordinator.async_refresh()
    assert coordinator.data.pending == {}
    assert coordinator.icon_for("pholder:450000000000000000001", "Test placeholder") == "mdi:gift"


async def test_add_validation(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Missing details and Parcel's refusals come back as clear errors."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    with pytest.raises(ServiceValidationError):
        await coordinator.async_add_package(tracking_number="hello", description="Mystery")
    with pytest.raises(ServiceValidationError):
        await coordinator.async_add_package(tracking_number="W1234567890", description="Phone")
    with pytest.raises(ServiceValidationError):
        await coordinator.async_add_package(
            tracking_number="1Z999AA10123456784", description="Again"
        )
    mock_parcel.add.side_effect = ParcelRequestError("Tracking number entered is not valid.")
    with pytest.raises(ServiceValidationError):
        await coordinator.async_add_package(tracking_number="1Z999AA10123456711", description="Bad")


async def test_delete_uses_stored_number_and_confirms(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Delete looks up what Parcel stored, deletes it, and checks it's gone."""
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    stored = {
        "tracking_number": "1Z999AA10123456784",
        "carrier_code": "ups",
        "label": "Coffee grinder",
    }
    mock_parcel.web_list.side_effect = [[stored], []]
    events = async_capture_events(hass, EVENT_PACKAGE_UPDATE)
    await coordinator.async_delete_package("ups:1Z999AA10123456784")
    await hass.async_block_till_done()
    mock_parcel.web_delete.assert_awaited_once_with("1Z999AA10123456784", "ups")
    assert "ups:1Z999AA10123456784" not in coordinator.data.deliveries
    assert events[-1].data["type"] == "removed"
    assert events[-1].data["reason"] == "deleted"


async def test_delete_not_confirmed(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """If the package is still listed afterwards, say so."""
    await setup(hass, config_entry)
    stored = {
        "tracking_number": "1Z999AA10123456784",
        "carrier_code": "ups",
        "label": "Coffee grinder",
    }
    mock_parcel.web_list.side_effect = [[stored], [stored]]
    with pytest.raises(HomeAssistantError):
        await config_entry.runtime_data.async_delete_package("ups:1Z999AA10123456784")


async def test_delete_with_expired_sign_in_raises_repair(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """An expired web sign-in creates a repair issue."""
    from homeassistant.helpers import issue_registry as ir

    await setup(hass, config_entry)
    mock_parcel.web_list.side_effect = ParcelWebAuthError("expired")
    with pytest.raises(HomeAssistantError):
        await config_entry.runtime_data.async_delete_package("ups:1Z999AA10123456784")
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_{config_entry.entry_id}")


async def test_delete_without_sign_in(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """Without the web sign-in, delete explains what's needed."""
    entry = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "k"}, options={})
    await setup(hass, entry)
    with pytest.raises(ServiceValidationError):
        await entry.runtime_data.async_delete_package("ups:1Z999AA10123456784")


async def test_restart_reuses_recent_data(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Reloading soon after a check doesn't spend another of Parcel's 20 checks an hour."""
    await setup(hass, config_entry)
    assert mock_parcel.get.await_count == 1
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_parcel.get.await_count == 1
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"


async def test_unload(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Unloading removes the panel along with the last account."""
    await setup(hass, config_entry)
    with patch("custom_components.parcel.async_unregister_panel") as unregister:
        assert await hass.config_entries.async_unload(config_entry.entry_id)
    unregister.assert_called_once()
