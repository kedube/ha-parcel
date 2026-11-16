"""Connecting an account, re-entering a revoked key, and options."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.parcel.api import ParcelAuthError, ParcelConnectionError, ParcelWebAuthError
from custom_components.parcel.const import CONF_ACCOUNT_TOKEN, DOMAIN


async def test_user_flow(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """A working key creates the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": " good-key "}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"api_key": "good-key"}


async def test_user_flow_errors(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """Rejected keys and network trouble are explained, and the form stays open."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_parcel.get.side_effect = ParcelAuthError("Account not found")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "bad"})
    assert result["errors"] == {"base": "invalid_auth"}
    mock_parcel.get.side_effect = ParcelConnectionError("offline")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "bad"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_key_aborts(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """The same key can't be added twice."""
    MockConfigEntry(domain=DOMAIN, data={"api_key": "same"}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "same"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """After revoking a key, the new one replaces it."""
    entry = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "old"})
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "new"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new"


async def test_options_with_web_sign_in(hass: HomeAssistant, mock_parcel: SimpleNamespace) -> None:
    """A pasted cookie string is reduced to the token and checked."""
    entry = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "k"})
    entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        mock_parcel.web_list.side_effect = ParcelWebAuthError("bad")
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                "package_sensors": False,
                CONF_ACCOUNT_TOKEN: "account_token=abc123; weblanguage=en",
            },
        )
        assert result["errors"] == {CONF_ACCOUNT_TOKEN: "invalid_account_token"}
        mock_parcel.web_list.side_effect = None
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                "package_sensors": False,
                CONF_ACCOUNT_TOKEN: "account_token=abc123; weblanguage=en",
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["scan_interval"] == 10
    assert entry.options["package_sensors"] is False
    assert entry.options[CONF_ACCOUNT_TOKEN] == "abc123"
    assert entry.options["account_token_set_at"] is not None
