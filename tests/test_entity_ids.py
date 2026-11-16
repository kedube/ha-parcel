"""Package sensors: unique IDs that don't give away tracking numbers, readable entity IDs.

Home Assistant keeps a removed sensor's unique ID and entity ID in its entity
registry for as long as the account is set up, so neither may hold a tracking number.
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry, flush_store

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import check_until_gone
from .test_init import setup
from custom_components.parcel.const import CONF_ACCOUNT_TOKEN, CONF_PACKAGE_ID_SECRET, DOMAIN
from custom_components.parcel.entity import package_id

UPS = "1Z999AA10123456784"
AMAZON = "TBA312345678901"
UPS_KEY = f"ups:{UPS}"
SECRET = "a" * 32
OPAQUE = re.compile(r"[0-9a-f]{16}")


def account(**kwargs: Any) -> MockConfigEntry:
    """An account like the conftest one; minor_version and data as the test needs."""
    data = {"api_key": "test-key", **kwargs.pop("data", {})}
    return MockConfigEntry(
        domain=DOMAIN,
        title="Parcel",
        data=data,
        options={"scan_interval": 5, "package_sensors": True, CONF_ACCOUNT_TOKEN: "test-token"},
        **kwargs,
    )


async def start(hass: HomeAssistant, entry: MockConfigEntry) -> bool:
    """Set up an account that is already added to hass."""
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        started = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return started


def old_sensor(hass: HomeAssistant, entry: MockConfigEntry, key: str, object_id: str) -> Any:
    """A package sensor as versions before 1.2 registered it."""
    return er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_package_{key}",
        config_entry=entry,
        suggested_object_id=object_id,
    )


def test_the_id_depends_on_the_package_and_the_account() -> None:
    one = account(data={CONF_PACKAGE_ID_SECRET: SECRET})
    two = account(data={CONF_PACKAGE_ID_SECRET: "b" * 32})
    made = package_id(one, UPS_KEY)
    assert OPAQUE.fullmatch(made)
    assert package_id(one, UPS_KEY) == made
    assert package_id(two, UPS_KEY) != made
    assert package_id(one, f"usps:{UPS}") != made
    # Changing how the ID is made would give every package sensor a new one.
    assert made == "dc707b8453ba3b64"


async def test_package_sensors_get_ids_without_tracking_numbers(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    assert re.fullmatch(r"[0-9a-f]{32}", config_entry.data[CONF_PACKAGE_ID_SECRET])
    registry = er.async_get(hass)
    grinder = registry.async_get("sensor.parcel_coffee_grinder")
    assert grinder.unique_id == (
        f"{config_entry.entry_id}_package_{package_id(config_entry, UPS_KEY)}"
    )
    assert registry.async_get("sensor.parcel_dog_food") is not None
    for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        for number in (UPS, AMAZON):
            assert number not in entity.unique_id
            assert number.lower() not in entity.entity_id


async def test_a_removed_sensor_leaves_no_tracking_number_in_the_registry(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, config_entry)
    del deliveries[0]  # Parcel no longer lists the coffee grinder
    await check_until_gone(hass, config_entry, freezer)

    registry = er.async_get(hass)
    assert registry.async_get("sensor.parcel_coffee_grinder") is None
    kept = [
        deleted
        for deleted in registry.deleted_entities.values()
        if deleted.config_entry_id == config_entry.entry_id
    ]
    # Home Assistant keeps it so the entity ID comes back if the package does.
    assert [deleted.entity_id for deleted in kept] == ["sensor.parcel_coffee_grinder"]

    await flush_store(registry._store)
    saved = json.dumps(hass_storage["core.entity_registry"])
    assert UPS not in saved
    assert AMAZON not in saved


async def test_a_package_without_a_name_keeps_its_number_out_of_the_entity_id(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    deliveries[0]["description"] = ""
    await setup(hass, config_entry)
    state = hass.states.get("sensor.parcel_ups_package")
    assert state.state == "in_transit"
    # Parcel shows such a package by its number, and so does its sensor's name.
    assert state.attributes["friendly_name"] == f"Parcel {UPS}"
    assert hass.states.get(f"sensor.parcel_{UPS.lower()}") is None


async def test_old_ids_move_to_new_ones_and_everything_else_stays(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    entry = account(minor_version=1)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = old_sensor(hass, entry, UPS_KEY, "parcel_coffee_grinder")
    registry.async_update_entity(old.entity_id, name="Grinder")
    summary = registry.async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_on_the_way", config_entry=entry
    )
    # Its unique ID starts like a package sensor's.
    event = registry.async_get_or_create(
        "event", DOMAIN, f"{entry.entry_id}_package_update", config_entry=entry
    )

    assert await start(hass, entry)
    assert entry.minor_version == 2
    moved = registry.async_get("sensor.parcel_coffee_grinder")
    assert moved.id == old.id
    assert moved.unique_id == f"{entry.entry_id}_package_{package_id(entry, UPS_KEY)}"
    assert moved.name == "Grinder"
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"
    assert hass.states.get("sensor.parcel_coffee_grinder_2") is None
    assert registry.async_get(summary.entity_id).unique_id == summary.unique_id
    assert registry.async_get(event.entity_id).unique_id == event.unique_id


async def test_a_left_over_old_id_does_not_stop_the_move(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """Both IDs registered (say, after going back to an earlier version and forward again)."""
    entry = account(minor_version=1, data={CONF_PACKAGE_ID_SECRET: SECRET})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    current = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_package_{package_id(entry, UPS_KEY)}",
        config_entry=entry,
        suggested_object_id="parcel_coffee_grinder",
    )
    left_over = old_sensor(hass, entry, UPS_KEY, "parcel_coffee_grinder_2")

    assert await start(hass, entry)
    assert entry.data[CONF_PACKAGE_ID_SECRET] == SECRET
    assert registry.async_get(left_over.entity_id) is None
    assert registry.async_get("sensor.parcel_coffee_grinder").id == current.id
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"


async def test_a_new_account_keeps_its_secret(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """Made at the first setup; a reload must not make another and so new sensors."""
    entry = account(minor_version=2)  # as the setup form makes it
    entry.add_to_hass(hass)
    assert await start(hass, entry)
    secret = entry.data[CONF_PACKAGE_ID_SECRET]
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data[CONF_PACKAGE_ID_SECRET] == secret
    assert hass.states.get("sensor.parcel_coffee_grinder").state == "in_transit"
    assert hass.states.get("sensor.parcel_coffee_grinder_2") is None


async def test_an_account_saved_by_a_later_version_is_left_alone(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    entry = account(version=2)
    entry.add_to_hass(hass)
    assert not await start(hass, entry)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
