"""The diagnostics download leaves out keys, sign-ins and anything about the packages."""

from __future__ import annotations

import json
from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from .test_init import setup
from custom_components.parcel.api import ParcelConnectionError, ParcelRequestError
from custom_components.parcel.diagnostics import async_get_config_entry_diagnostics


async def test_nothing_personal_is_left_in(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    deliveries[0]["events"] = [
        {
            "event": "Delivered, signed by J SMITH at MEMPHIS TN",
            "date": "2026-11-15 08:14:00",
            "location": "Memphis, TN",
            "additional": "Left with neighbour at number 12",
        },
        # A date that can't be read is kept as the carrier wrote it.
        {"event": "Arrived", "date": "Leave at side gate, code 4821"},
    ]
    await setup(hass, config_entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    text = json.dumps(diagnostics)

    for private in (
        "test-key",
        "test-token",
        "1Z999AA10123456784",
        "TBA312345678901",
        "Coffee grinder",
        "Dog food",
        "J SMITH",
        "MEMPHIS",
        "Memphis",
        "neighbour",
        "123-456",
        "4821",
    ):
        assert private not in text, private

    # What helps with troubleshooting is still there.
    assert diagnostics["status"]["last_update_success"] is True
    assert diagnostics["status"]["web_sign_in_configured"] is True
    assert diagnostics["status"]["carriers_loaded"] == 7
    assert diagnostics["entry"]["options"]["scan_interval"] == 5
    assert len(diagnostics["deliveries"]) == 2
    first = diagnostics["deliveries"][0]
    assert first["carrier_code"] == "ups"
    assert first["status"] == "in_transit"
    assert first["events"][0]["date"] is not None


async def test_the_latest_problem_is_included(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    mock_parcel.get.side_effect = ParcelConnectionError("Couldn't reach Parcel: timed out")
    await config_entry.runtime_data.async_refresh()
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["status"]["last_error"] == "Couldn't reach Parcel: timed out"


async def test_a_package_named_in_an_error_is_left_out(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Parcel's own error text is kept, minus any tracking number or name in it."""
    await setup(hass, config_entry)
    mock_parcel.get.side_effect = ParcelRequestError(
        "Couldn't refresh 1Z999AA10123456784 (Coffee grinder)"
    )
    await config_entry.runtime_data.async_refresh()
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["status"]["last_error"] == "Couldn't refresh **REDACTED** (**REDACTED**)"
