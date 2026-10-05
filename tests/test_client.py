"""CoreApiClient error propagation, through a real httpx response.

Commands branch on ``httpx.HTTPStatusError`` and its status code (lane next's
404 = empty lane, lane claim's 404, proposals' 400/404). These tests run the
real ``_request`` against an in-process transport, so they prove the client
raises what those handlers catch.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest

from core_cli import client as client_mod
from core_cli.client import CoreApiClient, CoreApiError
from core_cli.resources.lane.next import next_finding


def _serve(status: int, body: dict) -> object:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    real = httpx.AsyncClient

    def factory(**kwargs: object) -> httpx.AsyncClient:
        return real(transport=transport, **kwargs)

    return patch.object(client_mod.httpx, "AsyncClient", factory)


async def test_success_returns_json() -> None:
    with _serve(200, {"proposals": []}):
        assert await CoreApiClient().list_proposals() == {"proposals": []}


async def test_error_status_raises_typed_error_with_detail() -> None:
    with (
        _serve(404, {"detail": "Proposal abc not found"}),
        pytest.raises(CoreApiError) as exc_info,
    ):
        await CoreApiClient().get_proposal("abc")
    err = exc_info.value
    assert isinstance(err, httpx.HTTPStatusError)
    assert err.status_code == 404
    assert err.response.status_code == 404
    assert err.detail == "Proposal abc not found"
    assert str(err) == "API error 404: Proposal abc not found"


async def test_lane_next_404_reports_empty_lane(capsys: pytest.CaptureFixture) -> None:
    """End to end: the command's 404 branch now fires on a real response."""
    with _serve(404, {"detail": "no delegated findings"}):
        await next_finding.__wrapped__()
    assert "Lane is empty" in capsys.readouterr().out


# -- Unix socket transport (CORE_API_URL=unix:///...) ------------------------


def test_parse_base_url_http_is_unchanged() -> None:
    assert client_mod.parse_base_url("http://10.0.0.5:8000") == (
        "http://10.0.0.5:8000",
        None,
    )


def test_parse_base_url_unix_gives_socket_path() -> None:
    assert client_mod.parse_base_url("unix:///run/core/api.sock") == (
        "http://localhost",
        "/run/core/api.sock",
    )


def test_parse_base_url_unix_relative_path_is_refused() -> None:
    with pytest.raises(ValueError, match="absolute path"):
        client_mod.parse_base_url("unix://run/core/api.sock")


def test_env_unix_url_selects_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORE_API_URL", "unix:///run/core/api.sock")
    assert CoreApiClient().socket_path == "/run/core/api.sock"


async def test_request_travels_over_the_unix_socket(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A real HTTP exchange over a real Unix socket, not a mocked transport."""
    socket_path = tmp_path_factory.mktemp("uds") / "api.sock"
    seen: list[bytes] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        seen.append(await reader.readuntil(b"\r\n\r\n"))
        body = b'{"proposals": []}'
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        await writer.drain()
        writer.close()

    server = await asyncio.start_unix_server(handle, path=str(socket_path))
    async with server:
        client = CoreApiClient(f"unix://{socket_path}")
        assert await client.list_proposals() == {"proposals": []}
    assert seen[0].startswith(b"GET /v1/proposals?limit=50 HTTP/1.1")
