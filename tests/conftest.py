"""Shared fixtures. Parcel is never contacted: its client methods are replaced with mocks."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.parcel.const import CONF_ACCOUNT_TOKEN, DOMAIN

CARRIERS = {
    "ups": {"name": "UPS"},
    "usps": {"name": "USPS"},
    "fedex": {"name": "FedEx"},
    "amzlus": {"name": "Amazon US"},
    "pholder": {"name": "Placeholder Delivery"},
    "apple": {"name": "Apple Store Orders", "extra": 2},
    "yodel": {"name": "Yodel", "extra": 1},
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Generator[None]:
    """Let Home Assistant load custom_components/parcel."""
    yield


def raw(
    number: str,
    carrier: str,
    name: str,
    status: int,
    *,
    events: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """One delivery as Parcel's API returns it."""
    return {
        "tracking_number": number,
        "carrier_code": carrier,
        "description": name,
        "status_code": status,
        "events": events or [],
        **extra,
    }


@pytest.fixture
def deliveries() -> list[dict[str, Any]]:
    """Packages in various states, including Amazon's date-only ETA and '--//--' dates."""
    return [
        raw(
            "1Z999AA10123456784",
            "ups",
            "Coffee grinder",
            2,
            events=[
                {"event": "In transit", "date": "2026-11-15 08:14:00", "location": "Portland, OR"}
            ],
            date_expected="2026-11-16 13:00:00",
            date_expected_end="2026-11-16 16:00:00",
        ),
        raw(
            "TBA312345678901",
            "amzlus",
            "Dog food",
            2,
            events=[{"event": "Package left the shipper facility", "date": "--//--"}],
            date_expected="2026-11-16 00:00:00",
            extra_information="123-456",
        ),
    ]


@pytest.fixture
def mock_parcel(deliveries: list[dict[str, Any]]) -> Generator[SimpleNamespace]:
    """Replace every call to Parcel."""
    with (
        patch(
            "custom_components.parcel.api.ParcelClient.async_get_deliveries",
            new_callable=AsyncMock,
            return_value=deliveries,
        ) as get,
        patch(
            "custom_components.parcel.api.ParcelClient.async_add_delivery", new_callable=AsyncMock
        ) as add,
        patch(
            "custom_components.parcel.carriers.async_fetch_carriers",
            new_callable=AsyncMock,
            return_value=CARRIERS,
        ),
        patch(
            "custom_components.parcel.api.ParcelWebClient.async_list_deliveries",
            new_callable=AsyncMock,
            return_value=[],
        ) as web_list,
        patch(
            "custom_components.parcel.api.ParcelWebClient.async_delete_delivery",
            new_callable=AsyncMock,
        ) as web_delete,
    ):
        yield SimpleNamespace(get=get, add=add, web_list=web_list, web_delete=web_delete)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """An account with deleting turned on."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Parcel",
        data={"api_key": "test-key"},
        options={"scan_interval": 5, "package_sensors": True, CONF_ACCOUNT_TOKEN: "test-token"},
    )
