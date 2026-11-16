"""When Parcel says "slow down": keep working from saved data and don't ask again early."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.parcel.api import ParcelConnectionError, ParcelRateLimitError
from custom_components.parcel.const import DOMAIN


def seed_cache(
    hass_storage: dict[str, Any], entry: MockConfigEntry, deliveries: list, hours_old: float
) -> None:
    """Pretend Home Assistant saved Parcel's response some time ago."""
    fetched_at = (dt_util.utcnow() - timedelta(hours=hours_old)).isoformat()
    key = f"{DOMAIN}.{entry.entry_id}"
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {
            "initialized": True,
            "cache": {"fetched_at": fetched_at, "deliveries": deliveries},
        },
    }


async def start(hass: HomeAssistant, entry: MockConfigEntry) -> bool:
    entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return result


async def test_rate_limit_at_startup_uses_saved_data(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """A 429 at startup doesn't take Parcel down; sensors show the last saved data."""
    seed_cache(hass_storage, config_entry, deliveries, hours_old=2)
    mock_parcel.get.side_effect = ParcelRateLimitError("slow down")
    assert await start(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"
    assert mock_parcel.get.await_count == 1
    # The panel is told checks are paused, and how old the data is.
    state = config_entry.runtime_data.panel_state()
    assert state["paused_until"] is not None
    assert state["last_error"] is None

    # Reloading during the pause asks Parcel nothing.
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_parcel.get.await_count == 1

    # A manual check explains the pause instead of claiming to be up to date.
    config_entry.runtime_data.data.fetched_at = None
    with pytest.raises(HomeAssistantError):
        await config_entry.runtime_data.async_manual_refresh()
    assert mock_parcel.get.await_count == 1


async def test_rate_limit_without_saved_data_retries_quietly(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    """With nothing saved, setup waits, and its retries don't ask Parcel again early."""
    mock_parcel.get.side_effect = ParcelRateLimitError("slow down")
    assert not await start(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert mock_parcel.get.await_count == 1

    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert mock_parcel.get.await_count == 1


async def test_success_ends_the_pause(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Once the pause is over and a check succeeds, normal polling resumes."""
    seed_cache(hass_storage, config_entry, deliveries, hours_old=2)
    mock_parcel.get.side_effect = ParcelRateLimitError("slow down")
    assert await start(hass, config_entry)
    coordinator = config_entry.runtime_data
    assert coordinator.storage.rate_limited_until(dt_util.utcnow()) is not None

    # Time passes; Parcel answers normally again.
    coordinator.storage.set_rate_limited_until(dt_util.utcnow() - timedelta(minutes=1))
    mock_parcel.get.side_effect = None
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.storage.rate_limited_until(dt_util.utcnow()) is None
    assert coordinator.update_interval == timedelta(minutes=5)
    assert coordinator.panel_state()["paused_until"] is None


async def test_rate_limit_while_running_keeps_packages_visible(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    """A 429 on a regular check keeps sensors available with their last values."""
    assert await start(hass, config_entry)
    coordinator = config_entry.runtime_data
    assert mock_parcel.get.await_count == 1

    mock_parcel.get.side_effect = ParcelRateLimitError("slow down", retry_after=45 * 60)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_parcel.get.await_count == 2
    assert coordinator.last_update_success
    assert hass.states.get("sensor.parcel_on_the_way").state == "2"
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"
    # Parcel's own "retry after" is respected when it's longer than the default pause.
    until = coordinator.storage.rate_limited_until(dt_util.utcnow())
    assert until is not None
    assert until - dt_util.utcnow() > timedelta(minutes=40)

    # The following scheduled checks ask Parcel nothing until the pause ends.
    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert mock_parcel.get.await_count == 2


@pytest.mark.parametrize("asked", [3.2e9, 1e20])
async def test_a_wait_of_years_is_cut_to_hours(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry, asked: float
) -> None:
    """However long Parcel asks for, checks pause for at most two hours."""
    assert await start(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_parcel.get.side_effect = ParcelRateLimitError("slow down", retry_after=asked)
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    until = coordinator.storage.rate_limited_until(dt_util.utcnow())
    assert until is not None
    assert timedelta(minutes=110) < until - dt_util.utcnow() <= timedelta(hours=2)


async def test_unreachable_at_startup_retries_as_usual(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Old saved data is only a stand-in during a rate limit, not when Parcel is down."""
    seed_cache(hass_storage, config_entry, deliveries, hours_old=2)
    mock_parcel.get.side_effect = ParcelConnectionError("offline")
    assert not await start(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
