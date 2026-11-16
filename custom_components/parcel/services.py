"""Actions for automations and scripts: add, delete and check packages."""

from __future__ import annotations

import re

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import ParcelCoordinator

SERVICE_ADD = "add_package"
SERVICE_DELETE = "delete_package"
SERVICE_REFRESH = "refresh"
ATTR_ENTRY = "config_entry_id"

ADD_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): cv.string,
        vol.Required("tracking_number"): cv.string,
        vol.Required("description"): cv.string,
        vol.Optional("carrier"): cv.string,
        vol.Optional("postcode"): cv.string,
        vol.Optional("email"): cv.string,
        vol.Optional("send_push_confirmation", default=False): cv.boolean,
    }
)
DELETE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): cv.string,
        vol.Required("tracking_number"): cv.string,
        vol.Optional("carrier"): cv.string,
    }
)
REFRESH_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY): cv.string})


def _targets(hass: HomeAssistant, entry_id: str | None, *, single: bool) -> list[ParcelCoordinator]:
    loaded = [
        entry
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
    ]
    if entry_id:
        for entry in loaded:
            if entry.entry_id == entry_id:
                return [entry.runtime_data]
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_not_loaded")
    if not loaded:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_set_up")
    if single and len(loaded) > 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="choose_account")
    return [entry.runtime_data for entry in loaded]


async def _async_add(call: ServiceCall) -> ServiceResponse:
    coordinator = _targets(call.hass, call.data.get(ATTR_ENTRY), single=True)[0]
    result = await coordinator.async_add_package(
        tracking_number=call.data["tracking_number"],
        description=call.data["description"],
        carrier_code=call.data.get("carrier"),
        extra=call.data.get("postcode") or call.data.get("email"),
        send_push_confirmation=call.data["send_push_confirmation"],
    )
    return result if call.return_response else None


async def _async_delete(call: ServiceCall) -> None:
    number = re.sub(r"\s+", "", call.data["tracking_number"])
    carrier = (call.data.get("carrier") or "").strip().lower() or None
    coordinator = _targets(call.hass, call.data.get(ATTR_ENTRY), single=True)[0]
    snapshot = coordinator.data
    keys: list[str] = []
    if snapshot is not None:
        keys += [
            key
            for key, delivery in snapshot.deliveries.items()
            if delivery.tracking_number.replace(" ", "") == number
            and (carrier is None or delivery.carrier_code == carrier)
        ]
        keys += [
            key
            for key, pending in snapshot.pending.items()
            if pending.tracking_number == number
            and (carrier is None or pending.carrier_code == carrier)
        ]
    if not keys:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="package_not_found")
    if len(keys) > 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="choose_carrier")
    await coordinator.async_delete_package(keys[0])


async def _async_refresh(call: ServiceCall) -> None:
    for coordinator in _targets(call.hass, call.data.get(ATTR_ENTRY), single=False):
        await coordinator.async_manual_refresh()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD,
        _async_add,
        schema=ADD_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_DELETE, _async_delete, schema=DELETE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _async_refresh, schema=REFRESH_SCHEMA)
