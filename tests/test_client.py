"""CoreApiClient error propagation, through a real httpx response.

Commands branch on ``httpx.HTTPStatusError`` and its status code (lane next's
404 = empty lane, lane claim's 404, proposals' 400/404). These tests run the
real ``_request`` against an in-process transport, so they prove the client
raises what those handlers catch.
"""

from __future__ import annotations

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
