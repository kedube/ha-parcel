"""Keeps an eye on the web sign-in that deleting relies on, and says when it needs replacing."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from .api import ParcelError, ParcelWebAuthError, ParcelWebClient
from .const import (
    CONF_ACCOUNT_TOKEN_SET_AT,
    DATA_WEB_SESSION,
    DOMAIN,
    WEB_SIGN_IN_CHECK_INTERVAL,
    WEB_SIGN_IN_DOCS_URL,
    WEB_SIGN_IN_FIRST_CHECK,
    WEB_TOKEN_LIFETIME,
    WEB_TOKEN_WARN_AHEAD,
)

_LOGGER = logging.getLogger(__name__)


@callback
def web_session(hass: HomeAssistant) -> aiohttp.ClientSession:
    """The session for Parcel's web app, shared by every account and the options form.

    It keeps no cookies: each request carries its own account's sign-in, and nothing
    a response sets is stored or sent with another request.
    """
    session: aiohttp.ClientSession | None = hass.data.get(DATA_WEB_SESSION)
    if session is None:
        session = async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar())
        hass.data[DATA_WEB_SESSION] = session
    return session


def expired_issue_id(entry_id: str) -> str:
    """The repair shown when Parcel no longer accepts the sign-in."""
    return f"web_sign_in_{entry_id}"


def expiring_issue_id(entry_id: str) -> str:
    """The heads-up shown shortly before the sign-in reaches its 360 days."""
    return f"web_sign_in_expiring_{entry_id}"


@callback
def async_clear_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Remove both notices, for example when the sign-in is replaced or the account removed."""
    ir.async_delete_issue(hass, DOMAIN, expired_issue_id(entry_id))
    ir.async_delete_issue(hass, DOMAIN, expiring_issue_id(entry_id))


class WebSignInMonitor:
    """Checks one account's web sign-in daily and raises or clears its repair notices."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: ParcelWebClient | None
    ) -> None:
        """Client is None when no web sign-in is configured; then nothing is checked."""
        self.hass = hass
        self.client = client
        self._entry = entry
        self._unsub_daily: CALLBACK_TYPE | None = None
        self._unsub_first: CALLBACK_TYPE | None = None

    @callback
    def async_start(self) -> None:
        """Begin checking daily, and once shortly after startup."""
        if self.client is None or self._unsub_daily is not None:
            return
        self._unsub_daily = async_track_time_interval(
            self.hass, self._start_check, WEB_SIGN_IN_CHECK_INTERVAL
        )
        self._unsub_first = async_call_later(self.hass, WEB_SIGN_IN_FIRST_CHECK, self._first_check)

    @callback
    def async_stop(self) -> None:
        """Stop the timers."""
        for name in ("_unsub_daily", "_unsub_first"):
            if cancel := getattr(self, name):
                cancel()
                setattr(self, name, None)

    @callback
    def _first_check(self, now: datetime) -> None:
        self._unsub_first = None
        self._start_check(now)

    @callback
    def _start_check(self, _now: datetime | None = None) -> None:
        """Check as a task of the account's, so unloading or removing it cancels the check."""
        self._entry.async_create_background_task(
            self.hass, self.async_check(), f"{DOMAIN} web sign-in check"
        )

    def remaining(self) -> timedelta | None:
        """How long until the pasted token reaches its 360-day lifetime, if known."""
        stamp = self._entry.options.get(CONF_ACCOUNT_TOKEN_SET_AT)
        set_at = dt_util.parse_datetime(stamp) if stamp else None
        if set_at is None:
            return None
        return (set_at + WEB_TOKEN_LIFETIME) - dt_util.utcnow()

    @callback
    def async_mark_expired(self) -> None:
        """Parcel rejected the sign-in: ask for a new one, and drop the softer notice."""
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            expired_issue_id(self._entry.entry_id),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="web_sign_in_expired",
            translation_placeholders={"title": self._entry.title},
            learn_more_url=WEB_SIGN_IN_DOCS_URL,
        )
        ir.async_delete_issue(self.hass, DOMAIN, expiring_issue_id(self._entry.entry_id))

    @callback
    def async_mark_working(self) -> None:
        """The sign-in just worked, so it hasn't expired."""
        ir.async_delete_issue(self.hass, DOMAIN, expired_issue_id(self._entry.entry_id))

    async def async_check(self, _now: datetime | None = None) -> None:
        """Confirm the token still works, and warn before it expires."""
        if self.client is None:
            return
        try:
            await self.client.async_validate()
        except ParcelWebAuthError:
            self.async_mark_expired()
            return
        except ParcelError as err:
            _LOGGER.debug("Couldn't check the Parcel web sign-in; will retry: %s", err)
            return
        self.async_mark_working()
        remaining = self.remaining()
        issue_id = expiring_issue_id(self._entry.entry_id)
        if remaining is not None and remaining <= WEB_TOKEN_WARN_AHEAD:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="web_sign_in_expiring",
                translation_placeholders={
                    "title": self._entry.title,
                    "days": str(max(0, remaining.days)),
                },
                learn_more_url=WEB_SIGN_IN_DOCS_URL,
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
