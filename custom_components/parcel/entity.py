"""Shared base for Parcel entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PARCEL_WEB_URL
from .coordinator import ParcelCoordinator


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
