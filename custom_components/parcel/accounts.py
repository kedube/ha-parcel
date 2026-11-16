"""Finding the loaded Parcel accounts, for actions and the panel's commands."""

from __future__ import annotations

from homeassistant.auth.models import User
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import ParcelCoordinator


@callback
def loaded_coordinators(hass: HomeAssistant) -> list[ParcelCoordinator]:
    """Every account that is set up and running."""
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
    ]


@callback
def coordinators_for(hass: HomeAssistant, entry_id: str | None) -> list[ParcelCoordinator]:
    """The named account, or every loaded account when none is named."""
    loaded = loaded_coordinators(hass)
    if entry_id is None:
        return loaded
    for coordinator in loaded:
        if coordinator.config_entry.entry_id == entry_id:
            return [coordinator]
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_not_loaded")


@callback
def one_coordinator(hass: HomeAssistant, entry_id: str | None) -> ParcelCoordinator:
    """The account to act on: the named one, or the only one when none is named."""
    coordinators = coordinators_for(hass, entry_id)
    if not coordinators:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_set_up")
    if len(coordinators) > 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="choose_account")
    return coordinators[0]


@callback
def may_change(hass: HomeAssistant, user: User) -> bool:
    """Whether a person may add, delete or check packages, or change an icon.

    The same rule Home Assistant applies to the actions: anyone who may control a
    Parcel entity. That's admins and regular users; read-only users can only look.
    """
    if user.is_admin:
        return True
    return any(
        user.permissions.check_entity(entry.entity_id, POLICY_CONTROL)
        for entry in er.async_get(hass).entities.values()
        if entry.platform == DOMAIN
    )
