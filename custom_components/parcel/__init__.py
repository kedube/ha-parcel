"""Parcel: package tracking for Home Assistant, with a Packages sidebar panel."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import ParcelClient, ParcelWebClient
from .carriers import CarrierRegistry
from .const import CONF_ACCOUNT_TOKEN, DATA_CARRIERS, DOMAIN
from .coordinator import ParcelConfigEntry, ParcelCoordinator
from .entity import device_info
from .panel import async_notify_panel, async_register_panel, async_unregister_panel
from .services import async_setup_services
from .storage import ParcelStorage
from .web_sign_in import async_clear_issues, web_session
from .websocket import async_setup_websocket

PLATFORMS = [Platform.BUTTON, Platform.EVENT, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up what all Parcel accounts share."""
    hass.data[DATA_CARRIERS] = CarrierRegistry(hass)
    async_setup_websocket(hass)
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ParcelConfigEntry) -> bool:
    """Set up one Parcel account."""
    carriers: CarrierRegistry = hass.data[DATA_CARRIERS]
    storage = ParcelStorage(hass, entry.entry_id)
    await storage.async_load()
    client = ParcelClient(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    token = entry.options.get(CONF_ACCOUNT_TOKEN)
    web_client = ParcelWebClient(web_session(hass), token) if token else None
    coordinator = ParcelCoordinator(hass, entry, client, storage, carriers, web_client)

    # Created here rather than by the first entity, because events carry its id.
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **device_info(entry)
    )
    coordinator.device_id = device.id

    await carriers.async_ensure_loaded()
    if not await coordinator.async_restore_from_cache():
        try:
            await coordinator.async_config_entry_first_refresh()
        except ConfigEntryNotReady:
            # While Parcel is rate-limiting, start from the last saved data instead
            # of failing setup, so the packages stay visible during the pause.
            # (If Parcel is unreachable, fail as usual and let Home Assistant retry.)
            if not (
                coordinator.requests_paused()
                and await coordinator.async_restore_from_cache(allow_stale=True)
            ):
                raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_add_listener(lambda: async_notify_panel(hass)))
    await async_register_panel(hass)
    async_notify_panel(hass)
    coordinator.web_sign_in.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ParcelConfigEntry) -> bool:
    """Unload one Parcel account; remove the panel with the last one."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        others = [
            other
            for other in hass.config_entries.async_loaded_entries(DOMAIN)
            if other.entry_id != entry.entry_id
        ]
        if not others:
            async_unregister_panel(hass)
        async_notify_panel(hass, exclude=entry.entry_id)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ParcelConfigEntry) -> None:
    """Delete what was stored for a removed account, and its repair notices."""
    await ParcelStorage(hass, entry.entry_id).async_remove()
    async_clear_issues(hass, entry.entry_id)


__all__ = ["ParcelCoordinator"]
