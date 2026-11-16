"""An event entity that fires on every package change."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EVENT_TYPES
from .coordinator import ParcelConfigEntry, ParcelCoordinator
from .entity import ParcelEntity

ATTRIBUTES = (
    "description",
    "tracking_number",
    "carrier",
    "status",
    "previous_status",
    "message",
    "reason",
    "event",
    "location",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParcelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the package update event entity."""
    async_add_entities([ParcelUpdateEvent(entry.runtime_data)])


class ParcelUpdateEvent(ParcelEntity, EventEntity):
    """Fires added, out_for_delivery, delivered, needs_attention and more."""

    _attr_translation_key = "package_update"
    _attr_event_types = EVENT_TYPES

    def __init__(self, coordinator: ParcelCoordinator) -> None:
        """Set up."""
        super().__init__(coordinator, "package_update")

    async def async_added_to_hass(self) -> None:
        """Start listening for package changes."""
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_event_listener(self._handle))

    @callback
    def _handle(self, event_type: str, data: dict[str, Any]) -> None:
        self._trigger_event(
            event_type, {key: data[key] for key in ATTRIBUTES if data.get(key) is not None}
        )
        self.async_write_ha_state()
