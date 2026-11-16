"""Connecting an account, re-entering a revoked key, and options."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from .conftest import raw
from custom_components.parcel.api import (
    ParcelAuthError,
    ParcelConnectionError,
    ParcelRateLimitError,
    ParcelWebAuthError,
)
from custom_components.parcel.const import (
    CONF_ACCOUNT_TOKEN,
    CONF_ACCOUNT_TOKEN_SET_AT,
    CONF_REMOVE_ACCOUNT_TOKEN,
    DOMAIN,
)
from custom_components.parcel.web_sign_in import expired_issue_id


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
    # Current, so no migration runs; the ID secret is made at the first setup.
    assert result["result"].minor_version == 2


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


async def test_reauth_on_a_running_account_reloads_it_once(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The new key is saved and the account restarts once, the way Home Assistant asks for."""
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.parcel.async_register_panel", new_callable=AsyncMock
    ) as registered:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert registered.await_count == 1
        result = await config_entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "new-key"}
        )
        await hass.async_block_till_done()
        assert registered.await_count == 2
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["api_key"] == "new-key"
    assert config_entry.state is ConfigEntryState.LOADED
    # Home Assistant warns (and from 2026.12 refuses) when a reload listener is also in play.
    assert "update listener" not in caplog.text


SAVED = {
    "scan_interval": 5,
    "package_sensors": True,
    CONF_ACCOUNT_TOKEN: "saved-token",
    CONF_ACCOUNT_TOKEN_SET_AT: "2026-01-01T00:00:00+00:00",
}


def entry_with_sign_in() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title="Parcel", data={"api_key": "k"}, options=dict(SAVED)
    )


async def test_options_never_show_the_saved_sign_in(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """The saved sign-in isn't sent back to the browser; a switch offers to remove it."""
    entry = entry_with_sign_in()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fields = {str(key): key for key in result["data_schema"].schema}
    assert CONF_REMOVE_ACCOUNT_TOKEN in fields
    token_field = fields[CONF_ACCOUNT_TOKEN]
    assert not (token_field.description or {}).get("suggested_value")
    assert "saved-token" not in repr(result)

    # With nothing saved there is nothing to remove.
    bare = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "k2"})
    bare.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(bare.entry_id)
    assert CONF_REMOVE_ACCOUNT_TOKEN not in {str(key) for key in result["data_schema"].schema}


async def test_an_empty_box_keeps_the_saved_sign_in(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    entry = entry_with_sign_in()
    entry.add_to_hass(hass)
    ir.async_create_issue(
        hass,
        DOMAIN,
        expired_issue_id(entry.entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="web_sign_in_expired",
        translation_placeholders={"title": "Parcel"},
    )
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"scan_interval": 15, "package_sensors": True}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {**SAVED, "scan_interval": 15}
    mock_parcel.web_list.assert_not_awaited()
    # A notice about that sign-in still applies.
    assert ir.async_get(hass).async_get_issue(DOMAIN, expired_issue_id(entry.entry_id))


async def test_the_saved_sign_in_can_be_removed(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    entry = entry_with_sign_in()
    entry.add_to_hass(hass)
    ir.async_create_issue(
        hass,
        DOMAIN,
        expired_issue_id(entry.entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="web_sign_in_expired",
        translation_placeholders={"title": "Parcel"},
    )
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 5, "package_sensors": True, CONF_REMOVE_ACCOUNT_TOKEN: True},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_ACCOUNT_TOKEN] is None
    assert entry.options[CONF_ACCOUNT_TOKEN_SET_AT] is None
    assert CONF_REMOVE_ACCOUNT_TOKEN not in entry.options
    assert ir.async_get(hass).async_get_issue(DOMAIN, expired_issue_id(entry.entry_id)) is None


async def test_a_new_sign_in_replaces_the_saved_one(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    """The countdown to expiry starts again, and notices about the old one go."""
    entry = entry_with_sign_in()
    entry.add_to_hass(hass)
    ir.async_create_issue(
        hass,
        DOMAIN,
        expired_issue_id(entry.entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="web_sign_in_expired",
        translation_placeholders={"title": "Parcel"},
    )
    with patch("custom_components.parcel.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 5, "package_sensors": True, CONF_ACCOUNT_TOKEN: "fresh-token"},
        )
    assert entry.options[CONF_ACCOUNT_TOKEN] == "fresh-token"
    assert entry.options[CONF_ACCOUNT_TOKEN_SET_AT] != SAVED[CONF_ACCOUNT_TOKEN_SET_AT]
    assert ir.async_get(hass).async_get_issue(DOMAIN, expired_issue_id(entry.entry_id)) is None


async def test_sign_in_problems_are_explained(
    hass: HomeAssistant, mock_parcel: SimpleNamespace
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Parcel", data={"api_key": "k"})
    entry.add_to_hass(hass)
    form = {"scan_interval": 5, "package_sensors": True}
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Something that couldn't be a cookie value is refused without asking Parcel.
    for pasted in ("two words", "line\nbreak", "caf\u00e9"):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {**form, CONF_ACCOUNT_TOKEN: pasted}
        )
        assert result["errors"] == {CONF_ACCOUNT_TOKEN: "invalid_account_token"}
    mock_parcel.web_list.assert_not_awaited()

    mock_parcel.web_list.side_effect = ParcelRateLimitError("slow down")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**form, CONF_ACCOUNT_TOKEN: "abc123"}
    )
    assert result["errors"] == {CONF_ACCOUNT_TOKEN: "rate_limited"}
    # What was just typed is kept in the form for another try.
    fields = {str(key): key for key in result["data_schema"].schema}
    assert fields[CONF_ACCOUNT_TOKEN].description == {"suggested_value": "abc123"}


async def test_saving_options_restarts_the_account(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """A changed option takes effect straight away."""
    config_entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert config_entry.runtime_data.update_interval == timedelta(minutes=5)
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        await hass.config_entries.options.async_configure(
            result["flow_id"], {"scan_interval": 15, "package_sensors": True}
        )
        await hass.async_block_till_done()
    assert config_entry.runtime_data.update_interval == timedelta(minutes=15)
    assert config_entry.runtime_data.web_client is not None


async def test_a_sign_in_whose_list_writes_amazon_orders_its_own_way_is_accepted(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
) -> None:
    """Only Amazon orders on their way, which the web app writes "<order number>@<code>"."""
    deliveries[:] = [
        raw("113-4567890-1234567", "amzlus", "Kettle", 4, extra_information="Ab3Cd9EfG")
    ]
    config_entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        mock_parcel.web_list.side_effect = None
        mock_parcel.web_list.return_value = [
            {
                "tracking_number": "113-4567890-1234567@Ab3Cd9EfG",
                "carrier_code": "amzlus",
                "label": "Kettle",
            }
        ]
        form = {"scan_interval": 5, "package_sensors": True, CONF_ACCOUNT_TOKEN: "new-token"}
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], form)
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ACCOUNT_TOKEN] == "new-token"


async def test_a_sign_in_from_another_account_is_refused(
    hass: HomeAssistant, mock_parcel: SimpleNamespace, config_entry: MockConfigEntry
) -> None:
    """Its list must hold at least one of this account's packages on their way."""
    config_entry.add_to_hass(hass)
    with patch("custom_components.parcel.async_register_panel", new_callable=AsyncMock):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        form = {"scan_interval": 5, "package_sensors": True, CONF_ACCOUNT_TOKEN: "their-token"}
        mock_parcel.web_list.side_effect = None
        mock_parcel.web_list.return_value = [
            {"tracking_number": "9400111202555842332669", "carrier_code": "usps", "label": "x"}
        ]
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], form)
        assert result["errors"] == {CONF_ACCOUNT_TOKEN: "account_token_other_account"}

        mock_parcel.web_list.return_value = [
            {"tracking_number": "TBA312345678901", "carrier_code": "amzlus", "label": "x"}
        ]
        result = await hass.config_entries.options.async_configure(result["flow_id"], form)
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ACCOUNT_TOKEN] == "their-token"
