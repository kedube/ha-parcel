"""A button to check Parcel right away."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ParcelConfigEntry, ParcelCoordinator
from .entity import ParcelEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParcelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the check-now button."""
    async_add_entities([ParcelCheckNowButton(entry.runtime_data)])


class ParcelCheckNowButton(ParcelEntity, ButtonEntity):
    """Check Parcel for updates now (within Parcel's 20 checks an hour)."""

    _attr_translation_key = "check_now"

    def __init__(self, coordinator: ParcelCoordinator) -> None:
        """Set up."""
        super().__init__(coordinator, "check_now")

    async def async_press(self) -> None:
        """Check now."""
        await self.coordinator.async_manual_refresh()
