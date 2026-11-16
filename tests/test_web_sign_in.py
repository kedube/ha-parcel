"""The daily web sign-in check: expiry warning, early sign-out, and self-heal."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .test_init import setup
from custom_components.parcel.api import ParcelConnectionError, ParcelWebAuthError
from custom_components.parcel.const import (
    CONF_ACCOUNT_TOKEN,
    CONF_ACCOUNT_TOKEN_SET_AT,
    DOMAIN,
    WEB_TOKEN_LIFETIME,
)


def entry_with_token_age(days_old: int) -> MockConfigEntry:
    """An account whose web sign-in was entered a given number of days ago."""
    set_at = (dt_util.utcnow() - timedelta(days=days_old)).isoformat()
    return MockConfigEntry(
        domain=DOMAIN,
        title="Parcel",
        data={"api_key": "k"},
        options={
            "scan_interval": 5,
            "package_sensors": True,
            CONF_ACCOUNT_TOKEN: "tok",
            CONF_ACCOUNT_TOKEN_SET_AT: set_at,
        },
    )


async def test_warns_when_expiry_is_near(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """Within two weeks of the 360-day limit, a heads-up appears with days left."""
    entry = entry_with_token_age(WEB_TOKEN_LIFETIME.days - 10)
    await setup(hass, entry)
    await entry.runtime_data._async_check_web_sign_in()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_expiring_{entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders["days"] in {"9", "10"}


async def test_no_warning_when_plenty_of_time(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """A fresh token raises nothing."""
    entry = entry_with_token_age(30)
    await setup(hass, entry)
    await entry.runtime_data._async_check_web_sign_in()
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_expiring_{entry.entry_id}") is None
    )
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_{entry.entry_id}") is None


async def test_early_sign_out_detected_and_healed(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """A rejected token raises the expired notice, which clears once it works again."""
    entry = entry_with_token_age(30)
    await setup(hass, entry)
    coordinator = entry.runtime_data
    mock_parcel.web_list.side_effect = ParcelWebAuthError("signed out")
    await coordinator._async_check_web_sign_in()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_{entry.entry_id}") is not None

    mock_parcel.web_list.side_effect = None
    mock_parcel.web_list.return_value = []
    await coordinator._async_check_web_sign_in()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_{entry.entry_id}") is None


async def test_transient_error_changes_nothing(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """A network blip doesn't raise or clear anything."""
    entry = entry_with_token_age(WEB_TOKEN_LIFETIME.days - 10)
    await setup(hass, entry)
    coordinator = entry.runtime_data
    await coordinator._async_check_web_sign_in()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_expiring_{entry.entry_id}")
    mock_parcel.web_list.side_effect = ParcelConnectionError("offline")
    await coordinator._async_check_web_sign_in()
    # The warning from the previous successful check is untouched.
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"web_sign_in_expiring_{entry.entry_id}")


async def test_no_checks_without_web_sign_in(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """With no web sign-in configured, the check does nothing and never touches Parcel."""
    entry = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "k"}, options={})
    await setup(hass, entry)
    await entry.runtime_data._async_check_web_sign_in()
    mock_parcel.web_list.assert_not_called()


async def test_options_records_token_timestamp(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """Saving a token stamps when it was entered, for the expiry countdown."""
    entry = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "k"})
    entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 5, "package_sensors": True, CONF_ACCOUNT_TOKEN: "abc123"},
        )
    assert entry.options[CONF_ACCOUNT_TOKEN] == "abc123"
    stamp = dt_util.parse_datetime(entry.options[CONF_ACCOUNT_TOKEN_SET_AT])
    assert stamp is not None
    assert abs((dt_util.utcnow() - stamp).total_seconds()) < 30
