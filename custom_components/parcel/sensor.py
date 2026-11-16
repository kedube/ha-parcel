"""Summary sensors ("3 out for delivery") and optional per-package sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_PACKAGE_SENSORS
from .coordinator import ParcelConfigEntry, ParcelCoordinator
from .entity import ParcelEntity
from .models import STATUS_OPTIONS, Delivery, join_names
from .summary import Summary

PACKAGE_PREFIX = "package_"


def _sentence(items: list[Delivery], none: str, one: str, many: str) -> str:
    if not items:
        return none
    if len(items) == 1:
        return one.format(name=items[0].description)
    return many.format(count=len(items))


@dataclass(frozen=True, kw_only=True)
class ParcelSummaryDescription(SensorEntityDescription):
    """A count of packages with a ready-made sentence."""

    items_fn: Callable[[Summary], list[Delivery]]
    none: str
    one: str
    many: str


SUMMARY_SENSORS: tuple[ParcelSummaryDescription, ...] = (
    ParcelSummaryDescription(
        key="out_for_delivery",
        translation_key="out_for_delivery",
        items_fn=lambda s: s.out_for_delivery,
        none="No packages are out for delivery",
        one="{name} is out for delivery",
        many="{count} packages are out for delivery",
    ),
    ParcelSummaryDescription(
        key="arriving_today",
        translation_key="arriving_today",
        items_fn=lambda s: s.arriving_today,
        none="No packages arrive today",
        one="{name} arrives today",
        many="{count} packages arrive today",
    ),
    ParcelSummaryDescription(
        key="needs_attention",
        translation_key="needs_attention",
        items_fn=lambda s: s.needs_attention,
        none="No packages need attention",
        one="{name} needs attention",
        many="{count} packages need attention",
    ),
    ParcelSummaryDescription(
        key="ready_for_pickup",
        translation_key="ready_for_pickup",
        items_fn=lambda s: s.ready_for_pickup,
        none="No packages are waiting for pickup",
        one="{name} is ready for pickup",
        many="{count} packages are ready for pickup",
    ),
    ParcelSummaryDescription(
        key="on_the_way",
        translation_key="on_the_way",
        items_fn=lambda s: s.on_the_way,
        none="No packages are on the way",
        one="{name} is on the way",
        many="{count} packages are on the way",
    ),
    ParcelSummaryDescription(
        key="delivered_today",
        translation_key="delivered_today",
        items_fn=lambda s: s.delivered_today,
        none="Nothing has been delivered today",
        one="{name} was delivered today",
        many="{count} packages were delivered today",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParcelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the summary sensors, and keep per-package sensors in step with Parcel."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(ParcelSummarySensor(coordinator, description) for description in SUMMARY_SENSORS),
            ParcelNextDeliverySensor(coordinator),
            ParcelNextDeliveryDaySensor(coordinator),
        ]
    )

    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_{PACKAGE_PREFIX}"
    enabled = entry.options.get(CONF_PACKAGE_SENSORS, True)
    current: set[str] = set()

    @callback
    def sync_packages() -> None:
        data = coordinator.data
        wanted = (
            {
                key
                for key, delivery in data.deliveries.items()
                if coordinator.wants_package_sensor(delivery)
            }
            if enabled and data
            else set()
        )
        new = wanted - current
        if new:
            async_add_entities([ParcelPackageSensor(coordinator, key) for key in sorted(new)])
            current.update(new)
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg_entry.domain != "sensor" or not reg_entry.unique_id.startswith(prefix):
                continue
            if reg_entry.unique_id.removeprefix(prefix) not in wanted:
                registry.async_remove(reg_entry.entity_id)
                current.discard(reg_entry.unique_id.removeprefix(prefix))

    sync_packages()
    entry.async_on_unload(coordinator.async_add_listener(sync_packages))


class ParcelSummarySensor(ParcelEntity, SensorEntity):
    """How many packages are in a given situation."""

    entity_description: ParcelSummaryDescription
    _attr_native_unit_of_measurement = "packages"
    # The full list changes with every tracking update; history only needs the count.
    _unrecorded_attributes = frozenset({"packages"})

    def __init__(
        self, coordinator: ParcelCoordinator, description: ParcelSummaryDescription
    ) -> None:
        """Set up from a description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    def _items(self) -> list[Delivery]:
        return self.entity_description.items_fn(self.coordinator.summary())

    @property
    def native_value(self) -> int:
        """Number of packages."""
        return len(self._items())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Names, a sentence for notifications, and tracking details."""
        items = self._items()
        d = self.entity_description
        return {
            "message": _sentence(items, d.none, d.one, d.many),
            "names": join_names([item.description for item in items]),
            "packages": [
                {
                    "name": item.description,
                    "carrier": self.coordinator.carriers.name(item.carrier_code),
                    "tracking_number": item.tracking_number,
                    "status": item.status,
                }
                for item in items
            ],
        }


class ParcelNextDeliverySensor(ParcelEntity, SensorEntity):
    """When the next delivery window starts, for packages whose carrier gave a time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_delivery"

    def __init__(self, coordinator: ParcelCoordinator) -> None:
        """Set up."""
        super().__init__(coordinator, "next_delivery")

    @property
    def native_value(self) -> datetime | None:
        """Start of the next known delivery window.

        Unknown when carriers have only given days; the next delivery day sensor
        covers those, so a day never shows up here as "midnight".
        """
        return self.coordinator.summary().next_timed_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Which package, and when its window ends."""
        delivery = self.coordinator.summary().next_timed
        if delivery is None:
            return {"package": None}
        return {
            "package": delivery.description,
            "carrier": self.coordinator.carriers.name(delivery.carrier_code),
            "tracking_number": delivery.tracking_number,
            "window_end": delivery.eta_end.isoformat() if delivery.eta_end else None,
        }


class ParcelNextDeliveryDaySensor(ParcelEntity, SensorEntity):
    """The next day a package is expected, whether or not a time is known."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "next_delivery_day"

    def __init__(self, coordinator: ParcelCoordinator) -> None:
        """Set up."""
        super().__init__(coordinator, "next_delivery_day")

    @property
    def native_value(self) -> date | None:
        """The day."""
        return self.coordinator.summary().next_day

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """What is expected that day."""
        items = self.coordinator.summary().next_day_deliveries
        return {
            "package": items[0].description if items else None,
            "names": join_names([item.description for item in items]),
            "count": len(items),
        }


class ParcelPackageSensor(ParcelEntity, SensorEntity):
    """One package: its status, with details as attributes."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_translation_key = "package"

    def __init__(self, coordinator: ParcelCoordinator, key: str) -> None:
        """Track one package by its carrier and tracking number."""
        super().__init__(coordinator, f"{PACKAGE_PREFIX}{key}")
        self._key = key
        delivery = coordinator.data.deliveries.get(key) if coordinator.data else None
        self._name = delivery.description if delivery else key

    @property
    def _delivery(self) -> Delivery | None:
        data = self.coordinator.data
        return data.deliveries.get(self._key) if data else None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Follow the package's name when it's changed in Parcel."""
        if (delivery := self._delivery) is not None:
            self._name = delivery.description
        super()._handle_coordinator_update()

    @property
    def name(self) -> str:
        """The package's name in Parcel."""
        return self._name

    @property
    def available(self) -> bool:
        """Available while Parcel still lists the package."""
        return super().available and self._delivery is not None

    @property
    def native_value(self) -> str | None:
        """Status, such as out_for_delivery."""
        delivery = self._delivery
        return delivery.status if delivery else None

    @property
    def icon(self) -> str | None:
        """The package's icon (chosen, or guessed from its name)."""
        delivery = self._delivery
        return self.coordinator.icon_for(self._key, delivery.description) if delivery else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Tracking details."""
        delivery = self._delivery
        if delivery is None:
            return {}
        latest = delivery.latest_event
        delivered = self.coordinator.delivered_at(delivery)
        return {
            "description": delivery.description,
            "carrier": self.coordinator.carriers.name(delivery.carrier_code),
            "carrier_code": delivery.carrier_code,
            "tracking_number": delivery.tracking_number,
            "expected": (
                delivery.eta_date.isoformat()
                if delivery.eta_date
                else delivery.eta_start.isoformat()
                if delivery.eta_start
                else None
            ),
            "expected_end": delivery.eta_end.isoformat() if delivery.eta_end else None,
            "last_update": latest.text if latest else None,
            "last_update_at": latest.when.isoformat() if latest and latest.when else None,
            "last_location": latest.location if latest else None,
            "delivered_at": delivered.isoformat() if delivered else None,
        }
