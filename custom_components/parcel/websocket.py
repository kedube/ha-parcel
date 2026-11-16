"""Commands the Packages panel uses to read and change packages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import probatio as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import translation

from .accounts import coordinators_for, one_coordinator
from .carriers import CarrierRegistry
from .const import DATA_CARRIERS, DATA_SUBSCRIBERS, DOMAIN
from .models import CARRIER_PATTERNS
from .panel import panel_payload, suggested_carriers


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the panel's commands."""
    for handler in (ws_subscribe, ws_refresh, ws_add, ws_delete, ws_set_icon, ws_carriers):
        websocket_api.async_register_command(hass, handler)


async def _message(hass: HomeAssistant, err: HomeAssistantError) -> str:
    """The error's friendly sentence from translations, falling back to its text."""
    if err.translation_domain == DOMAIN and err.translation_key:
        strings = await translation.async_get_translations(
            hass, hass.config.language, "exceptions", [DOMAIN]
        )
        template = strings.get(f"component.{DOMAIN}.exceptions.{err.translation_key}.message")
        if template:
            try:
                return template.format(**(err.translation_placeholders or {}))
            except (KeyError, IndexError, ValueError):
                return template
    return str(err) or "Something went wrong"


@websocket_api.websocket_command({vol.Required("type"): "parcel/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Stream package data to the panel until it closes."""
    subscribers: set[Callable[[dict[str, Any]], None]] = hass.data.setdefault(
        DATA_SUBSCRIBERS, set()
    )

    @callback
    def send(payload: dict[str, Any]) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], payload))

    @callback
    def unsubscribe() -> None:
        subscribers.discard(send)

    subscribers.add(send)
    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send(panel_payload(hass))


@websocket_api.websocket_command(
    {vol.Required("type"): "parcel/refresh", vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_refresh(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Check Parcel now."""
    try:
        for coordinator in coordinators_for(hass, msg.get("entry_id")):
            await coordinator.async_manual_refresh()
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "refresh_failed", await _message(hass, err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "parcel/add",
        vol.Optional("entry_id"): str,
        vol.Required("tracking_number"): str,
        vol.Required("description"): str,
        vol.Optional("carrier_code"): vol.Any(str, None),
        vol.Optional("extra"): vol.Any(str, None),
        vol.Optional("send_push_confirmation", default=False): bool,
        vol.Optional("icon"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_add(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Add a package."""
    try:
        result = await one_coordinator(hass, msg.get("entry_id")).async_add_package(
            tracking_number=msg["tracking_number"],
            description=msg["description"],
            carrier_code=msg.get("carrier_code"),
            extra=msg.get("extra"),
            send_push_confirmation=msg["send_push_confirmation"],
            icon=msg.get("icon"),
        )
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "add_failed", await _message(hass, err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): "parcel/delete", vol.Required("entry_id"): str, vol.Required("key"): str}
)
@websocket_api.async_response
async def ws_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a package from Parcel."""
    try:
        await one_coordinator(hass, msg["entry_id"]).async_delete_package(msg["key"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "delete_failed", await _message(hass, err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "parcel/set_icon",
        vol.Required("entry_id"): str,
        vol.Required("key"): str,
        vol.Required("icon"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_set_icon(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change a package's icon (stored in Home Assistant only)."""
    try:
        one_coordinator(hass, msg["entry_id"]).async_set_icon(msg["key"], msg["icon"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "set_icon_failed", await _message(hass, err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "parcel/carriers"})
@websocket_api.async_response
async def ws_carriers(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Parcel's carriers, the number patterns used to suggest one, and common picks."""
    registry: CarrierRegistry = hass.data[DATA_CARRIERS]
    carriers = await registry.async_ensure_loaded()
    connection.send_result(
        msg["id"],
        {
            "carriers": carriers,
            "detect": [{"pattern": pattern, "code": code} for pattern, code in CARRIER_PATTERNS],
            "suggested": [code for code in suggested_carriers(hass) if code in carriers],
        },
    )
