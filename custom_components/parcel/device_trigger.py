"""Automation triggers you can pick in the editor, like "A package was delivered"."""

from __future__ import annotations

from typing import Any

import probatio as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    EVENT_ADDED,
    EVENT_DELIVERED,
    EVENT_NEEDS_ATTENTION,
    EVENT_OUT_FOR_DELIVERY,
    EVENT_PACKAGE_UPDATE,
    EVENT_READY_FOR_PICKUP,
)

# Trigger type → the event type it listens for (None means any change).
TRIGGERS: dict[str, str | None] = {
    "package_delivered": EVENT_DELIVERED,
    "package_out_for_delivery": EVENT_OUT_FOR_DELIVERY,
    "package_needs_attention": EVENT_NEEDS_ATTENTION,
    "package_ready_for_pickup": EVENT_READY_FOR_PICKUP,
    "package_added": EVENT_ADDED,
    "package_update": None,
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({vol.Required(CONF_TYPE): vol.In(TRIGGERS)})


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    """Triggers for a Parcel account's device."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None or not any(identifier[0] == DOMAIN for identifier in device.identifiers):
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: trigger,
        }
        for trigger in TRIGGERS
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for this account's package events of the chosen type."""
    event_data: dict[str, Any] = {"device_id": config[CONF_DEVICE_ID]}
    if (event_type := TRIGGERS[config[CONF_TYPE]]) is not None:
        event_data["type"] = event_type
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_PACKAGE_UPDATE,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
