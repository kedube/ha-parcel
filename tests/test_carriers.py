"""Parcel's carrier list: caching, backing off after a failed download, and short names."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant

from .conftest import CARRIERS
from custom_components.parcel.api import ParcelConnectionError
from custom_components.parcel.carriers import CarrierRegistry
from custom_components.parcel.const import CARRIER_LIST_MAX_AGE, CARRIER_RETRY_AFTER

FETCH = "custom_components.parcel.carriers.async_fetch_carriers"


async def test_the_list_is_downloaded_once_a_day(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    registry = CarrierRegistry(hass)
    with patch(FETCH, new_callable=AsyncMock, return_value=CARRIERS) as fetch:
        assert await registry.async_ensure_loaded() == CARRIERS
        await registry.async_ensure_loaded()
        assert fetch.await_count == 1
        freezer.tick(CARRIER_LIST_MAX_AGE + timedelta(minutes=1))
        await registry.async_ensure_loaded()
        assert fetch.await_count == 2


async def test_a_failed_download_is_not_tried_again_straight_away(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """While Parcel's list can't be reached, callers aren't each made to wait for a retry."""
    registry = CarrierRegistry(hass)
    with patch(FETCH, new_callable=AsyncMock, side_effect=ParcelConnectionError("slow")) as fetch:
        assert await registry.async_ensure_loaded() == {}
        assert await registry.async_ensure_loaded() == {}
        assert fetch.await_count == 1

        freezer.tick(CARRIER_RETRY_AFTER + timedelta(seconds=1))
        fetch.side_effect = None
        fetch.return_value = CARRIERS
        assert await registry.async_ensure_loaded() == CARRIERS
        assert fetch.await_count == 2


async def test_a_stale_list_keeps_working_when_the_download_fails(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    registry = CarrierRegistry(hass)
    with patch(FETCH, new_callable=AsyncMock, return_value=CARRIERS) as fetch:
        await registry.async_ensure_loaded()
        freezer.tick(CARRIER_LIST_MAX_AGE + timedelta(minutes=1))
        fetch.side_effect = ParcelConnectionError("offline")
        assert await registry.async_ensure_loaded() == CARRIERS
        assert registry.name("ups") == "UPS"


def test_short_names_keep_whole_words(hass: HomeAssistant) -> None:
    registry = CarrierRegistry(hass)
    registry.carriers = {
        "dp": {"name": "Deutsche Post"},
        "rm": {"name": "Royal Mail"},
        "col": {"name": "Colissimo"},
        "dhlgm": {"name": "DHL Global Mail (Germany)"},
        "long": {"name": "International Bridge Domestic Delivery"},
        "one": {"name": "Supercalifragilisticexpialidocious"},
    }
    assert registry.short_name("dp") == "Deutsche Post"
    assert registry.short_name("rm") == "Royal Mail"
    assert registry.short_name("col") == "Colissimo"
    assert registry.short_name("dhlgm") == "DHL Global Mail"
    assert registry.short_name("long") == "International"
    assert registry.short_name("one") == "Supercalifragilisticexpialidocious"
    assert registry.short_name("unknown") == "UNKNOWN"
    assert registry.extra("dp") == 0
