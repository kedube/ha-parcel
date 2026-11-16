"""Clients for Parcel's documented API and, for deletes only, its web app."""

from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Any

import aiohttp

from .const import (
    ADD_DELIVERY_URL,
    CARRIERS_URL,
    DELIVERIES_URL,
    WEB_AUTH_ERROR,
    WEB_BASE,
    WEB_COOKIE,
    WEB_DELETE_URL,
    WEB_LIST_URL,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
USER_AGENT = "HomeAssistant-Parcel (+https://github.com/kedube/ha-parcel)"


class ParcelError(Exception):
    """Something went wrong talking to Parcel."""


class ParcelConnectionError(ParcelError):
    """Parcel couldn't be reached."""


class ParcelAuthError(ParcelError):
    """Parcel rejected the API key."""


class ParcelRateLimitError(ParcelError):
    """Parcel's rate limit was reached."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Remember how long Parcel asked us to wait, if it said."""
        super().__init__(message)
        self.retry_after = retry_after


class ParcelRequestError(ParcelError):
    """Parcel refused the request, for example an unrecognized tracking number."""


class ParcelWebAuthError(ParcelError):
    """The web sign-in token was rejected (expired, signed out or mistyped)."""


def _retry_after(response: aiohttp.ClientResponse) -> float | None:
    """Seconds Parcel asked us to wait, when it said so in a usable way."""
    value = response.headers.get("Retry-After")
    try:
        seconds = float(value) if value else None
    except ValueError:
        return None
    return seconds if seconds is not None and math.isfinite(seconds) and seconds >= 0 else None


async def _read_json(response: aiohttp.ClientResponse) -> Any:
    try:
        return json.loads(await response.text())
    except (ValueError, RecursionError) as err:
        # Not JSON, not text in its stated encoding, or nested too deeply to read.
        raise ParcelError(f"Parcel sent an unexpected response (HTTP {response.status})") from err


class ParcelClient:
    """Parcel's documented API, authorized with the account's API key."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        """Keep the session and key."""
        self._session = session
        self._api_key = api_key

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"api-key": self._api_key, "User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                # No redirects: aiohttp drops only its standard credential headers when
                # one leads elsewhere, so the api-key header would go along with it.
                async with self._session.request(
                    method, url, headers=headers, params=params, json=payload, allow_redirects=False
                ) as response:
                    status = response.status
                    if 300 <= status < 400:
                        raise ParcelError(f"Parcel sent an unexpected redirect (HTTP {status})")
                    if status == 429:
                        raise ParcelRateLimitError(
                            "Parcel's rate limit was reached", _retry_after(response)
                        )
                    try:
                        data = await _read_json(response)
                    except ParcelError:
                        if status in (401, 403):
                            # Refused, even though the reply isn't in the usual format.
                            raise ParcelAuthError(
                                f"Parcel refused the API key (HTTP {status})"
                            ) from None
                        raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ParcelConnectionError(f"Couldn't reach Parcel: {err}") from err

        if not isinstance(data, dict):
            raise ParcelError(f"Parcel sent an unexpected response (HTTP {status})")
        if data.get("success") is True:
            return data
        message = str(data.get("error_message") or f"HTTP {status}")
        lowered = message.lower()
        if status in (401, 403) or "account not found" in lowered or "api key" in lowered:
            raise ParcelAuthError(message)
        if "limit" in lowered or "too many" in lowered:
            raise ParcelRateLimitError(message)
        raise ParcelRequestError(message)

    async def async_get_deliveries(self, filter_mode: str = "recent") -> list[dict[str, Any]]:
        """Active and recently delivered packages (Parcel's cached copy)."""
        data = await self._request("GET", DELIVERIES_URL, params={"filter_mode": filter_mode})
        deliveries = data.get("deliveries") or []
        if not isinstance(deliveries, list):
            raise ParcelError("Parcel sent deliveries in an unexpected format")
        return [item for item in deliveries if isinstance(item, dict)]

    async def async_add_delivery(
        self,
        *,
        tracking_number: str,
        carrier_code: str,
        description: str,
        language: str = "en",
        send_push_confirmation: bool = False,
        postcode: str | None = None,
        email: str | None = None,
    ) -> None:
        """Add a package. Parcel allows 20 of these a day, failures included."""
        payload: dict[str, Any] = {
            "tracking_number": tracking_number,
            "carrier_code": carrier_code,
            "description": description,
            "language": language,
            "send_push_confirmation": send_push_confirmation,
        }
        if postcode:
            payload["postcode"] = postcode
        if email:
            payload["email"] = email
        await self._request("POST", ADD_DELIVERY_URL, payload=payload)


async def async_fetch_carriers(session: aiohttp.ClientSession) -> dict[str, dict[str, Any]]:
    """Parcel's public list of carriers (no key needed)."""
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(CARRIERS_URL, headers={"User-Agent": USER_AGENT}) as response:
                response.raise_for_status()
                data = await _read_json(response)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ParcelConnectionError(f"Couldn't load Parcel's carrier list: {err}") from err
    if not isinstance(data, dict):
        raise ParcelError("Parcel's carrier list is in an unexpected format")
    carriers: dict[str, dict[str, Any]] = {}
    for code, info in data.items():
        if not isinstance(info, dict) or not info.get("name"):
            continue
        entry: dict[str, Any] = {"name": str(info["name"])}
        try:
            extra = int(info.get("extra_required") or 0)
        except (TypeError, ValueError):
            extra = 0
        if extra:
            entry["extra"] = extra
        carriers[str(code)] = entry
    return carriers


def normalize_account_token(value: str | None) -> str:
    """Accept the bare token, 'account_token=…', or a whole copied cookie string."""
    text = (value or "").strip().strip('"').strip("'")
    if f"{WEB_COOKIE}=" in text:
        text = text.split(f"{WEB_COOKIE}=", 1)[1].split(";", 1)[0]
    return text.strip()


class ParcelWebClient:
    """Parcel's web app, authorized with the account_token sign-in cookie.

    Parcel doesn't document these calls. They're what web.parcelapp.net itself
    sends, and they're used here only because the documented API can't delete.
    """

    def __init__(self, session: aiohttp.ClientSession, account_token: str) -> None:
        """Keep the session and token."""
        self._session = session
        self._token = account_token

    async def _post(self, url: str, form: dict[str, str]) -> dict[str, Any]:
        headers = {
            "Cookie": f"{WEB_COOKIE}={self._token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": f"{WEB_BASE}/",
        }
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.post(
                    url, data=form, headers=headers, allow_redirects=False
                ) as response:
                    if response.status in (301, 302, 303, 401, 403):
                        raise ParcelWebAuthError("Parcel's web app asked to sign in again")
                    if response.status == 429:
                        raise ParcelRateLimitError("Parcel's web app is rate limiting requests")
                    data = await _read_json(response)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ParcelConnectionError(f"Couldn't reach Parcel's web app: {err}") from err

        if not isinstance(data, dict):
            raise ParcelError("Parcel's web app sent an unexpected response")
        if data.get("success") is True:
            return data
        error = str(data.get("error") or data.get("error_message") or "unknown error")
        if error == WEB_AUTH_ERROR:
            raise ParcelWebAuthError("Parcel didn't accept the web sign-in token")
        raise ParcelRequestError(error)

    async def async_list_deliveries(self) -> list[dict[str, Any]]:
        """Every package in the account, as the web app downloads them (read-only)."""
        try:
            data = await self._post(WEB_LIST_URL, {"existing_deliveries": "[]"})
        except ParcelRequestError as err:
            # Parcel answers "missing_data" when no usable sign-in cookie arrives.
            if str(err) == "missing_data":
                raise ParcelWebAuthError("Parcel didn't receive a web sign-in token") from err
            raise
        items = data.get("deliveries_add") or []
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []

    async def async_validate(self) -> None:
        """Check the token with a read-only call."""
        await self.async_list_deliveries()

    async def async_delete_delivery(self, tracking_number: str, carrier_code: str) -> None:
        """Delete a package from the Parcel account, on all devices.

        Parcel reports success even when nothing matched, so callers should check
        the list afterwards.
        """
        await self._post(WEB_DELETE_URL, {"number": tracking_number, "type": carrier_code})
