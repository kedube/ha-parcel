"""Actions for automations and scripts: add, delete and check packages."""

from __future__ import annotations

import probatio as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import verify_domain_control

from .accounts import coordinators_for, one_coordinator
from .const import DOMAIN, MAX_NAME_LENGTH, MAX_NUMBER_LENGTH

SERVICE_ADD = "add_package"
SERVICE_DELETE = "delete_package"
SERVICE_REFRESH = "refresh"
ATTR_ENTRY = "config_entry_id"

NUMBER = vol.All(cv.string, vol.Length(max=MAX_NUMBER_LENGTH))
TEXT = vol.All(cv.string, vol.Length(max=MAX_NAME_LENGTH))

ADD_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): cv.string,
        vol.Required("tracking_number"): NUMBER,
        vol.Required("description"): TEXT,
        vol.Optional("carrier"): cv.string,
        vol.Optional("postcode"): TEXT,
        vol.Optional("email"): TEXT,
        vol.Optional("send_push_confirmation", default=False): cv.boolean,
    }
)
DELETE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): cv.string,
        vol.Required("tracking_number"): NUMBER,
        vol.Optional("carrier"): cv.string,
    }
)
REFRESH_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY): cv.string})


@verify_domain_control(DOMAIN)
async def _async_add(call: ServiceCall) -> ServiceResponse:
    coordinator = one_coordinator(call.hass, call.data.get(ATTR_ENTRY))
    result = await coordinator.async_add_package(
        tracking_number=call.data["tracking_number"],
        description=call.data["description"],
        carrier_code=call.data.get("carrier"),
        postcode=call.data.get("postcode"),
        email=call.data.get("email"),
        send_push_confirmation=call.data["send_push_confirmation"],
    )
    return result if call.return_response else None


@verify_domain_control(DOMAIN)
async def _async_delete(call: ServiceCall) -> None:
    coordinator = one_coordinator(call.hass, call.data.get(ATTR_ENTRY))
    carrier = (call.data.get("carrier") or "").strip().lower() or None
    keys = coordinator.find_keys(call.data["tracking_number"], carrier)
    if not keys:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="package_not_found")
    if len(keys) > 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="choose_carrier")
    await coordinator.async_delete_package(keys[0])


@verify_domain_control(DOMAIN)
async def _async_refresh(call: ServiceCall) -> None:
    coordinators = coordinators_for(call.hass, call.data.get(ATTR_ENTRY))
    if not coordinators:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_set_up")
    for coordinator in coordinators:
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
