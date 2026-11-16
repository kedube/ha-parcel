"""Setup, re-authentication and options for Parcel."""

from __future__ import annotations

from collections.abc import Mapping
import logging
import re
from typing import Any

import aiohttp
import probatio as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession, async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import dt as dt_util

from .api import (
    ParcelAuthError,
    ParcelClient,
    ParcelConnectionError,
    ParcelError,
    ParcelRateLimitError,
    ParcelWebAuthError,
    ParcelWebClient,
    normalize_account_token,
)
from .const import (
    API_KEY_DOCS_URL,
    CONF_ACCOUNT_TOKEN,
    CONF_ACCOUNT_TOKEN_SET_AT,
    CONF_PACKAGE_SENSORS,
    CONF_REMOVE_ACCOUNT_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    MAX_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
    PARCEL_WEB_URL,
    WEB_SIGN_IN_DOCS_URL,
)
from .web_sign_in import async_clear_issues

_LOGGER = logging.getLogger(__name__)

# A cookie value: visible characters only, none that would end it or start another.
TOKEN_FORMAT = re.compile(r"[!-~]+")
TOKEN_FORBIDDEN = frozenset(';," ')

API_KEY_SCHEMA = vol.Schema(
    {vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
)


async def _check_api_key(hass: HomeAssistant, api_key: str) -> str | None:
    """Return an error code, or None when Parcel accepts the key."""
    try:
        await ParcelClient(async_get_clientsession(hass), api_key).async_get_deliveries("active")
    except ParcelAuthError:
        return "invalid_auth"
    except ParcelRateLimitError:
        return "rate_limited"
    except ParcelConnectionError:
        return "cannot_connect"
    except ParcelError:
        _LOGGER.exception("Unexpected response from Parcel while checking the API key")
        return "unknown"
    return None


async def _check_account_token(hass: HomeAssistant, token: str) -> str | None:
    """Return an error code, or None when Parcel's web app accepts the token."""
    if not TOKEN_FORMAT.fullmatch(token) or TOKEN_FORBIDDEN & set(token):
        # Not something a browser would hold in a cookie, so don't send it anywhere.
        return "invalid_account_token"
    # auto_cleanup=False so this short-lived session is ours to close here, instead
    # of being tied to Home Assistant's shutdown.
    session = async_create_clientsession(
        hass, auto_cleanup=False, cookie_jar=aiohttp.DummyCookieJar()
    )
    try:
        await ParcelWebClient(session, token).async_validate()
    except ParcelWebAuthError:
        return "invalid_account_token"
    except ParcelRateLimitError:
        return "rate_limited"
    except ParcelConnectionError:
        return "cannot_connect"
    except ParcelError:
        _LOGGER.exception("Unexpected response from Parcel while checking the web sign-in")
        return "unknown"
    finally:
        await session.close()
    return None


class ParcelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Connect a Parcel account with its API key."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            self._async_abort_entries_match({CONF_API_KEY: api_key})
            if error := await _check_api_key(self.hass, api_key):
                errors["base"] = error
            else:
                return self.async_create_entry(title="Parcel", data={CONF_API_KEY: api_key})
        return self.async_show_form(
            step_id="user",
            data_schema=API_KEY_SCHEMA,
            errors=errors,
            description_placeholders={"web_url": PARCEL_WEB_URL, "docs_url": API_KEY_DOCS_URL},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Parcel stopped accepting the key, usually because it was revoked."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new API key."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            if error := await _check_api_key(self.hass, api_key):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=API_KEY_SCHEMA,
            errors=errors,
            description_placeholders={
                "title": entry.title,
                "web_url": PARCEL_WEB_URL,
                "docs_url": API_KEY_DOCS_URL,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ParcelOptionsFlow:
        """Options: check interval, per-package sensors and the web sign-in."""
        return ParcelOptionsFlow()


class ParcelOptionsFlow(OptionsFlowWithReload):
    """Change how Parcel behaves. Saving a change reloads the account."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One page of options."""
        errors: dict[str, str] = {}
        current = self.config_entry.options
        saved = current.get(CONF_ACCOUNT_TOKEN)
        if user_input is not None:
            # The saved sign-in is never shown in the form, so an empty box means
            # "keep it". It changes only when a new one is pasted or removal is chosen.
            pasted = normalize_account_token(user_input.get(CONF_ACCOUNT_TOKEN))
            token = saved
            set_at = current.get(CONF_ACCOUNT_TOKEN_SET_AT)
            if pasted and pasted != saved:
                if error := await _check_account_token(self.hass, pasted):
                    errors[CONF_ACCOUNT_TOKEN] = error
                # A fresh token restarts the countdown to its expiry.
                token, set_at = pasted, dt_util.utcnow().isoformat()
            elif user_input.get(CONF_REMOVE_ACCOUNT_TOKEN):
                token, set_at = None, None
            elif saved and not set_at:
                set_at = dt_util.utcnow().isoformat()
            if not errors:
                if token != saved:
                    # Notices about the old sign-in no longer apply.
                    async_clear_issues(self.hass, self.config_entry.entry_id)
                return self.async_create_entry(
                    data={
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                        CONF_PACKAGE_SENSORS: bool(user_input[CONF_PACKAGE_SENSORS]),
                        CONF_ACCOUNT_TOKEN: token or None,
                        CONF_ACCOUNT_TOKEN_SET_AT: set_at if token else None,
                    }
                )
        fields: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_MINUTES),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_MINUTES,
                    max=MAX_SCAN_MINUTES,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                CONF_PACKAGE_SENSORS, default=current.get(CONF_PACKAGE_SENSORS, True)
            ): BooleanSelector(),
            vol.Optional(CONF_ACCOUNT_TOKEN): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
        if saved:
            fields[vol.Optional(CONF_REMOVE_ACCOUNT_TOKEN, default=False)] = BooleanSelector()
        schema = vol.Schema(fields)
        if user_input is not None:
            # After an error, keep what was just typed (never the saved sign-in).
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"web_url": PARCEL_WEB_URL, "docs_url": WEB_SIGN_IN_DOCS_URL},
        )
