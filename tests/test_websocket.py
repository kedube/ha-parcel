"""The commands the Packages panel sends."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.auth.models import Credentials
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .conftest import CARRIERS
from .test_init import setup
from custom_components.parcel.api import ParcelRequestError
from custom_components.parcel.const import DATA_SUBSCRIBERS, READS_PER_HOUR

UPS_KEY = "ups:1Z999AA10123456784"


async def ask(client: Any, **message: Any) -> dict[str, Any]:
    """Send a command and return its answer."""
    await client.send_json_auto_id(message)
    return await client.receive_json()


async def test_subscribing_streams_the_packages(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass)
    answer = await ask(client, type="parcel/subscribe")
    assert answer["success"]
    first = await client.receive_json()
    assert first["type"] == "event"
    assert first["event"].keys() == {"entries"}
    entry = first["event"]["entries"][0]
    assert {d["key"] for d in entry["deliveries"]} == {UPS_KEY, "amzlus:TBA312345678901"}
    assert entry["adds_left"] == 20

    # A change at Parcel reaches the open panel.
    deliveries[0]["status_code"] = 4
    await config_entry.runtime_data.async_refresh()
    update = await client.receive_json()
    statuses = {d["key"]: d["status"] for d in update["event"]["entries"][0]["deliveries"]}
    assert statuses[UPS_KEY] == "out_for_delivery"

    # Closing the panel stops the stream.
    assert len(hass.data[DATA_SUBSCRIBERS]) == 1
    await client.close()
    await hass.async_block_till_done()
    assert hass.data[DATA_SUBSCRIBERS] == set()


async def test_adding_from_the_panel(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass)
    answer = await ask(
        client,
        type="parcel/add",
        tracking_number="1Z 999 AA1 01 2345 6799",
        description="Desk lamp",
        carrier_code=None,
        extra=None,
        icon="mdi:desk-lamp",
    )
    assert answer["result"] == {
        "key": "ups:1Z999AA10123456799",
        "carrier": "ups",
        "carrier_name": "UPS",
    }
    coordinator = config_entry.runtime_data
    assert coordinator.icon_for("ups:1Z999AA10123456799", "Desk lamp") == "mdi:desk-lamp"

    # Problems come back as a sentence the panel can show.
    answer = await ask(
        client, type="parcel/add", tracking_number="1z999aa10123456799", description="Again"
    )
    assert not answer["success"]
    assert answer["error"]["code"] == "add_failed"
    assert answer["error"]["message"] == "1z999aa10123456799 is already being tracked."

    mock_parcel.add.side_effect = ParcelRequestError("Tracking number entered is not valid.")
    answer = await ask(
        client, type="parcel/add", tracking_number="1Z999AA10123456711", description="Bad"
    )
    assert answer["error"]["message"] == (
        "Parcel didn't accept the package: Tracking number entered is not valid."
    )


async def test_deleting_and_icons_from_the_panel(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass)
    entry_id = config_entry.entry_id
    coordinator = config_entry.runtime_data

    answer = await ask(
        client, type="parcel/set_icon", entry_id=entry_id, key=UPS_KEY, icon="mdi:gift"
    )
    assert answer["success"]
    assert coordinator.icon_for(UPS_KEY, "Coffee grinder") == "mdi:gift"
    answer = await ask(client, type="parcel/set_icon", entry_id=entry_id, key=UPS_KEY, icon=None)
    assert coordinator.icon_for(UPS_KEY, "Coffee grinder") == "mdi:coffee"
    answer = await ask(
        client, type="parcel/set_icon", entry_id=entry_id, key="ups:NOPE", icon="mdi:gift"
    )
    assert answer["error"]["message"] == "Couldn't find that package."

    stored = {"tracking_number": "1Z999AA10123456784", "carrier_code": "ups", "label": "Coffee"}
    mock_parcel.web_list.side_effect = [[stored], []]
    answer = await ask(client, type="parcel/delete", entry_id=entry_id, key=UPS_KEY)
    assert answer["success"]
    mock_parcel.web_delete.assert_awaited_once_with("1Z999AA10123456784", "ups")
    assert UPS_KEY not in coordinator.data.deliveries

    answer = await ask(client, type="parcel/delete", entry_id=entry_id, key=UPS_KEY)
    assert answer["error"]["code"] == "delete_failed"
    assert answer["error"]["message"] == "Couldn't find that package."

    answer = await ask(client, type="parcel/delete", entry_id="not-an-account", key=UPS_KEY)
    assert answer["error"]["message"] == "That Parcel account isn't loaded."


async def test_carriers_for_the_add_form(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass)
    answer = await ask(client, type="parcel/carriers")
    result = answer["result"]
    assert result["carriers"] == CARRIERS
    assert {"pattern": "^1Z[0-9A-Z]{16}$", "code": "ups"} in result["detect"]
    assert set(result["suggested"]) >= {"ups", "amzlus"}
    assert set(result["suggested"]) <= set(CARRIERS)


async def test_checking_now_from_the_panel(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass)
    coordinator = config_entry.runtime_data

    # Just checked: nothing to do, and no check is spent.
    answer = await ask(client, type="parcel/refresh")
    assert answer["success"]
    assert mock_parcel.get.await_count == 1

    # Close to Parcel's hourly limit, it explains instead.
    coordinator.data.fetched_at = None
    now = dt_util.utcnow()
    for _ in range(READS_PER_HOUR):
        coordinator.storage.record_read(now)
    answer = await ask(client, type="parcel/refresh", entry_id=config_entry.entry_id)
    assert answer["error"]["code"] == "refresh_failed"
    assert answer["error"]["message"].startswith("Parcel allows 20 checks an hour")
    assert mock_parcel.get.await_count == 1


async def regular_user_token(hass: HomeAssistant) -> str:
    """A sign-in for someone who isn't an administrator (and isn't read-only either)."""
    user = MockUser(groups=[await hass.auth.async_get_group(GROUP_ID_USER)], name="household")
    user.add_to_hass(hass)
    credential = Credentials(
        id="household",
        auth_provider_type="homeassistant",
        auth_provider_id=None,
        data={"username": "household"},
        is_new=False,
    )
    user.credentials.append(credential)
    refresh = await hass.auth.async_create_refresh_token(
        user, "https://example.com/app", credential=credential
    )
    return hass.auth.async_create_access_token(refresh)


async def test_read_only_users_can_look_but_not_change(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    assert (await ask(client, type="parcel/subscribe"))["success"]
    await client.receive_json()  # the packages

    entry_id = config_entry.entry_id
    for message in (
        {"type": "parcel/add", "tracking_number": "9400111202555842332669", "description": "Socks"},
        {"type": "parcel/delete", "entry_id": entry_id, "key": UPS_KEY},
        {"type": "parcel/set_icon", "entry_id": entry_id, "key": UPS_KEY, "icon": "mdi:gift"},
        {"type": "parcel/refresh"},
    ):
        answer = await ask(client, **message)
        assert not answer["success"], message["type"]
        assert answer["error"]["code"] == "unauthorized", message["type"]
    # The actions are refused too (Home Assistant reports that as a general error).
    answer = await ask(
        client,
        type="call_service",
        domain="parcel",
        service="delete_package",
        service_data={"tracking_number": "1Z999AA10123456784"},
    )
    assert not answer["success"]
    assert answer["error"]["message"] == "Unauthorized"
    mock_parcel.add.assert_not_awaited()
    mock_parcel.web_delete.assert_not_awaited()
    assert config_entry.runtime_data.storage.icons == {}


async def test_household_members_can_change_packages(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    """Not only administrators: anyone who may control the account's entities."""
    await setup(hass, config_entry)
    client = await hass_ws_client(hass, await regular_user_token(hass))
    answer = await ask(
        client, type="parcel/set_icon", entry_id=config_entry.entry_id, key=UPS_KEY, icon="mdi:gift"
    )
    assert answer["success"]
    answer = await ask(
        client,
        type="call_service",
        domain="parcel",
        service="add_package",
        service_data={"tracking_number": "9400111202555842332669", "description": "Socks"},
    )
    assert answer["success"]
    mock_parcel.add.assert_awaited_once()


async def test_runaway_text_is_refused_before_parcel_sees_it(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    await setup(hass, config_entry)
    client = await hass_ws_client(hass)
    answer = await ask(
        client, type="parcel/add", tracking_number="9400111202555842332669", description="x" * 201
    )
    assert answer["error"]["code"] == "invalid_format"
    mock_parcel.add.assert_not_awaited()
