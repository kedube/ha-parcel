"""Talking to Parcel over HTTP: what is sent, and how each kind of answer is understood."""

from __future__ import annotations

from unittest.mock import patch

import aiohttp
from aiohttp import web as aioweb
from aiohttp.test_utils import TestServer
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.parcel.api import (
    ParcelAuthError,
    ParcelClient,
    ParcelConnectionError,
    ParcelError,
    ParcelRateLimitError,
    ParcelRequestError,
    ParcelWebAuthError,
    ParcelWebClient,
    async_fetch_carriers,
    normalize_account_token,
)
from custom_components.parcel.const import (
    ADD_DELIVERY_URL,
    CARRIERS_URL,
    DELIVERIES_URL,
    WEB_DELETE_URL,
    WEB_LIST_URL,
)

LIST_URL = f"{DELIVERIES_URL}?filter_mode=recent"


def client(hass: HomeAssistant) -> ParcelClient:
    return ParcelClient(async_get_clientsession(hass), "the-key")


def web(hass: HomeAssistant) -> ParcelWebClient:
    return ParcelWebClient(async_get_clientsession(hass), "the-token")


# The documented API ----------------------------------------------------------


async def test_deliveries_are_asked_for_with_the_key(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        LIST_URL,
        json={"success": True, "deliveries": [{"tracking_number": "1"}, "not a delivery"]},
    )
    assert await client(hass).async_get_deliveries() == [{"tracking_number": "1"}]
    _method, url, _data, headers = aioclient_mock.mock_calls[0]
    assert url.query["filter_mode"] == "recent"
    assert headers["api-key"] == "the-key"
    assert "HomeAssistant-Parcel" in headers["User-Agent"]


async def test_no_deliveries_is_an_empty_list(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(LIST_URL, json={"success": True})
    assert await client(hass).async_get_deliveries() == []
    aioclient_mock.clear_requests()
    aioclient_mock.get(LIST_URL, json={"success": True, "deliveries": {"oops": 1}})
    with pytest.raises(ParcelError):
        await client(hass).async_get_deliveries()


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (401, {"success": False, "error_message": "Account not found"}),
        (403, {"success": False, "error_message": "Forbidden"}),
        (200, {"success": False, "error_message": "Account not found"}),
        (200, {"success": False, "error_message": "Invalid API key"}),
    ],
)
async def test_a_refused_key_is_an_auth_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int, body: dict
) -> None:
    aioclient_mock.get(LIST_URL, status=status, json=body)
    with pytest.raises(ParcelAuthError):
        await client(hass).async_get_deliveries()


async def test_a_refusal_in_another_format_is_still_an_auth_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(LIST_URL, status=401, text="<html>Unauthorized</html>")
    with pytest.raises(ParcelAuthError):
        await client(hass).async_get_deliveries()


async def test_too_many_requests_carries_parcels_wait(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(LIST_URL, status=429, headers={"Retry-After": "120"}, text="slow down")
    with pytest.raises(ParcelRateLimitError) as raised:
        await client(hass).async_get_deliveries()
    assert raised.value.retry_after == 120

    # A wait that isn't a number of seconds (or is endless, or negative) is ignored.
    for unusable in ("soon", "inf", "nan", "-5"):
        aioclient_mock.clear_requests()
        aioclient_mock.get(LIST_URL, status=429, headers={"Retry-After": unusable}, text="")
        with pytest.raises(ParcelRateLimitError) as raised:
            await client(hass).async_get_deliveries()
        assert raised.value.retry_after is None, unusable

    aioclient_mock.clear_requests()
    aioclient_mock.get(LIST_URL, json={"success": False, "error_message": "Rate limit exceeded"})
    with pytest.raises(ParcelRateLimitError):
        await client(hass).async_get_deliveries()


@pytest.mark.parametrize(
    ("status", "kwargs"),
    [
        (500, {"text": "<html>Server error</html>"}),
        (200, {"text": "not json"}),
        (200, {"json": ["a", "list"]}),
    ],
)
async def test_an_answer_that_makes_no_sense_is_an_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int, kwargs: dict
) -> None:
    aioclient_mock.get(LIST_URL, status=status, **kwargs)
    with pytest.raises(ParcelError) as raised:
        await client(hass).async_get_deliveries()
    assert type(raised.value) is ParcelError


@pytest.mark.parametrize(
    "body", [b"\xff\xfe{\x00}", b"[" * 200_000], ids=["not utf-8", "nested too deeply"]
)
async def test_an_answer_that_cant_be_read_is_an_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, body: bytes
) -> None:
    """Like any other answer that makes no sense, so a short outage is still ridden out."""
    aioclient_mock.get(LIST_URL, content=body)
    with pytest.raises(ParcelError) as raised:
        await client(hass).async_get_deliveries()
    assert type(raised.value) is ParcelError


async def test_the_key_never_follows_a_redirect(hass: HomeAssistant, socket_enabled: None) -> None:
    """aiohttp would carry the api-key header along to wherever a redirect points."""
    reached: list[str] = []

    async def elsewhere(request: aioweb.Request) -> aioweb.Response:
        reached.append(request.headers.get("api-key", ""))
        return aioweb.json_response({"success": True, "deliveries": []})

    async def redirect(request: aioweb.Request) -> aioweb.Response:
        raise aioweb.HTTPFound(f"http://127.0.0.1:{other.port}/collect")

    servers = []
    for handler in (elsewhere, redirect):
        app = aioweb.Application()
        app.router.add_route("*", "/{tail:.*}", handler)
        servers.append(TestServer(app, host="127.0.0.1"))
        await servers[-1].start_server()
    other, source = servers
    try:
        url = f"http://127.0.0.1:{source.port}/external/deliveries/"
        with (
            patch("custom_components.parcel.api.DELIVERIES_URL", url),
            pytest.raises(ParcelError, match="redirect"),
        ):
            await client(hass).async_get_deliveries()
    finally:
        for server in servers:
            await server.close()
    assert reached == []


@pytest.mark.parametrize("failure", [TimeoutError(), aiohttp.ClientConnectionError("down")])
async def test_not_reaching_parcel_is_a_connection_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, failure: Exception
) -> None:
    aioclient_mock.get(LIST_URL, exc=failure)
    with pytest.raises(ParcelConnectionError):
        await client(hass).async_get_deliveries()


async def test_adding_sends_what_parcel_documents(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(ADD_DELIVERY_URL, json={"success": True})
    await client(hass).async_add_delivery(
        tracking_number="1Z999AA10123456784", carrier_code="ups", description="Coffee grinder"
    )
    assert aioclient_mock.mock_calls[0][2] == {
        "tracking_number": "1Z999AA10123456784",
        "carrier_code": "ups",
        "description": "Coffee grinder",
        "language": "en",
        "send_push_confirmation": False,
    }
    await client(hass).async_add_delivery(
        tracking_number="W1234567890",
        carrier_code="apple",
        description="Phone",
        language="fr",
        send_push_confirmation=True,
        postcode="90210",
        email="me@example.com",
    )
    sent = aioclient_mock.mock_calls[1][2]
    assert (sent["postcode"], sent["email"], sent["language"]) == ("90210", "me@example.com", "fr")
    assert sent["send_push_confirmation"] is True


async def test_a_rejected_add_says_why(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(
        ADD_DELIVERY_URL,
        status=400,
        json={"success": False, "error_message": "Tracking number entered is not valid."},
    )
    with pytest.raises(ParcelRequestError, match="not valid"):
        await client(hass).async_add_delivery(
            tracking_number="x", carrier_code="ups", description="Bad"
        )


# The carrier list ------------------------------------------------------------


async def test_the_carrier_list_keeps_names_and_extras(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        CARRIERS_URL,
        json={
            "ups": {"name": "UPS"},
            "apple": {"name": "Apple Store Orders", "extra_required": 2},
            "odd": {"name": "Odd", "extra_required": "x"},
            "nameless": {"extra_required": 1},
            "broken": "nope",
        },
    )
    assert await async_fetch_carriers(async_get_clientsession(hass)) == {
        "ups": {"name": "UPS"},
        "apple": {"name": "Apple Store Orders", "extra": 2},
        "odd": {"name": "Odd"},
    }


async def test_a_carrier_list_that_cant_be_had(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(CARRIERS_URL, status=503, text="")
    with pytest.raises(ParcelConnectionError):
        await async_fetch_carriers(async_get_clientsession(hass))
    aioclient_mock.clear_requests()
    aioclient_mock.get(CARRIERS_URL, json=["not", "a", "dict"])
    with pytest.raises(ParcelError):
        await async_fetch_carriers(async_get_clientsession(hass))


# The web app (for deleting) --------------------------------------------------


async def test_the_web_list_is_read_with_the_sign_in_cookie(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(
        WEB_LIST_URL,
        json={"success": True, "deliveries_add": [{"tracking_number": "1"}, "junk"]},
    )
    assert await web(hass).async_list_deliveries() == [{"tracking_number": "1"}]
    _method, _url, data, headers = aioclient_mock.mock_calls[0]
    assert data == {"existing_deliveries": "[]"}
    assert headers["Cookie"] == "account_token=the-token"
    await web(hass).async_validate()
    assert aioclient_mock.call_count == 2


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, {"success": False, "error": "failed_verification"}),
        (200, {"success": False, "error": "missing_data"}),
        (302, {}),
        (401, {}),
    ],
)
async def test_a_sign_in_parcel_no_longer_accepts(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int, body: dict
) -> None:
    aioclient_mock.post(WEB_LIST_URL, status=status, json=body)
    with pytest.raises(ParcelWebAuthError):
        await web(hass).async_list_deliveries()


async def test_other_web_app_answers(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(WEB_LIST_URL, status=429, text="")
    with pytest.raises(ParcelRateLimitError):
        await web(hass).async_list_deliveries()
    aioclient_mock.clear_requests()
    aioclient_mock.post(WEB_LIST_URL, json={"success": False, "error": "server_busy"})
    with pytest.raises(ParcelRequestError, match="server_busy"):
        await web(hass).async_list_deliveries()
    aioclient_mock.clear_requests()
    aioclient_mock.post(WEB_LIST_URL, exc=TimeoutError())
    with pytest.raises(ParcelConnectionError):
        await web(hass).async_list_deliveries()
    aioclient_mock.clear_requests()
    aioclient_mock.post(WEB_LIST_URL, json={"success": True, "deliveries_add": "nope"})
    assert await web(hass).async_list_deliveries() == []


async def test_deleting_names_the_number_and_carrier(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(WEB_DELETE_URL, json={"success": True})
    await web(hass).async_delete_delivery("1Z999AA10123456784", "ups")
    assert aioclient_mock.mock_calls[0][2] == {"number": "1Z999AA10123456784", "type": "ups"}

    aioclient_mock.clear_requests()
    # For a delete, "missing_data" is Parcel refusing the request, not the sign-in.
    aioclient_mock.post(WEB_DELETE_URL, json={"success": False, "error": "missing_data"})
    with pytest.raises(ParcelRequestError):
        await web(hass).async_delete_delivery("", "ups")


@pytest.mark.parametrize(
    ("pasted", "token"),
    [
        ("abc123", "abc123"),
        ("  abc123  ", "abc123"),
        ('"abc123"', "abc123"),
        ("account_token=abc123", "abc123"),
        ("weblanguage=en; account_token=abc123; other=1", "abc123"),
        ("", ""),
        (None, ""),
    ],
)
def test_a_pasted_sign_in_is_reduced_to_the_token(pasted: str | None, token: str) -> None:
    assert normalize_account_token(pasted) == token
