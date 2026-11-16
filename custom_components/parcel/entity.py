"""Shared base for Parcel entities."""

from __future__ import annotations

import hashlib
import hmac

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PACKAGE_ID_SECRET, DOMAIN, PARCEL_WEB_URL
from .coordinator import ParcelCoordinator

# A package sensor's unique ID is "<entry id>_package_<package_id(...)>".
PACKAGE_PREFIX = "package_"


def package_id(entry: ConfigEntry, key: str) -> str:
    """The part of a package sensor's unique ID that stands for the package.

    Home Assistant keeps unique IDs in its entity registry even after a sensor is
    removed, so this is a keyed hash of the package's carrier and tracking number
    (key), not the number itself. The account's random secret is the hash key, so
    the ID can't be checked against a guessed tracking number either.
    """
    secret = entry.data[CONF_PACKAGE_ID_SECRET].encode()
    return hmac.new(secret, key.encode(), hashlib.sha256).hexdigest()[:16]


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """The device that stands for one Parcel account and holds its entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Parcel",
        model="Package tracking",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=PARCEL_WEB_URL,
    )


class ParcelEntity(CoordinatorEntity[ParcelCoordinator]):
    """An entity on the account's Parcel device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ParcelCoordinator, key: str) -> None:
        """Attach to the account's device."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)
