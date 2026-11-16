"""The Packages sidebar panel: registered once, however many accounts there are."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.parcel.const import DOMAIN, PANEL_ELEMENT, PANEL_URL, STATIC_URL
from custom_components.parcel.models import ICON_CHOICES, ICON_RULES
from custom_components.parcel.panel import (
    async_register_panel,
    panel_config,
    panel_payload,
    suggested_carriers,
)


def account(key: str, title: str = "Parcel") -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, title=title, data={"api_key": key}, options={})


async def test_two_accounts_starting_together_share_one_panel(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """Home Assistant sets up a domain's accounts at the same time; both must load."""
    first = account("k1", "Home")
    second = account("k2", "Work")
    first.add_to_hass(hass)
    second.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED
    assert PANEL_URL in hass.data[frontend.DATA_PANELS]
    assert [entry["title"] for entry in panel_payload(hass)["entries"]] == ["Home", "Work"]

    # The panel stays while one account is left, and goes with the last one.
    assert await hass.config_entries.async_unload(first.entry_id)
    assert PANEL_URL in hass.data[frontend.DATA_PANELS]
    assert [entry["title"] for entry in panel_payload(hass)["entries"]] == ["Work"]
    assert await hass.config_entries.async_unload(second.entry_id)
    assert PANEL_URL not in hass.data[frontend.DATA_PANELS]

    # And it comes back when an account is loaded again.
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL in hass.data[frontend.DATA_PANELS]


async def test_registering_twice_at_once_is_harmless(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    await asyncio.gather(*(async_register_panel(hass) for _ in range(5)))
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL]
    assert panel.sidebar_title == "Packages"
    assert panel.require_admin is False
    assert panel.config["_panel_custom"]["name"] == PANEL_ELEMENT
    assert panel.config["_panel_custom"]["module_url"].startswith(
        f"{STATIC_URL}/parcel-panel.js?v="
    )


async def test_things_that_never_change_are_sent_once(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """Icon rules and choices come with the panel itself, not with every update."""
    entry = account("k1")
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    config = hass.data[frontend.DATA_PANELS][PANEL_URL].config
    assert config["static_url"] == STATIC_URL
    assert config["icon_choices"] == list(ICON_CHOICES)
    assert len(config["icon_rules"]) == len(ICON_RULES)
    assert config["icon_rules"][0].keys() == {"pattern", "icon"}
    assert panel_config().keys() == {"static_url", "icon_rules", "icon_choices"}

    payload = panel_payload(hass)
    assert payload.keys() == {"entries"}
    state = payload["entries"][0]
    assert state["entry_id"] == entry.entry_id
    assert state["can_delete"] is False
    assert len(state["deliveries"]) == 2
    assert {"key", "status", "carrier_name", "carrier_short", "icon"} <= state["deliveries"][
        0
    ].keys()


async def test_suggested_carriers_start_with_the_ones_in_use(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    hass.config.country = "US"
    entry = account("k1")
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    suggestions = suggested_carriers(hass)
    assert set(suggestions[:2]) == {"ups", "amzlus"}
    assert suggestions[2:] == ["usps", "fedex", "dhl", "ont"]
    hass.config.country = "DE"
    assert set(suggested_carriers(hass)) == {"ups", "amzlus"}
