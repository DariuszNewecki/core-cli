# tests/test_lane.py

"""Unit tests for lane CLI commands — stub the HTTP client layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import typer

from core_cli.resources.lane.claim import claim
from core_cli.resources.lane.list import list_delegated
from core_cli.resources.lane.next import next_finding

# Patch targets: where CoreApiClient is imported in each module.
_LIST_CLIENT = "core_cli.resources.lane.list.CoreApiClient"
_CLAIM_CLIENT = "core_cli.resources.lane.claim.CoreApiClient"
_NEXT_CLIENT = "core_cli.resources.lane.next.CoreApiClient"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_error(status_code: int, detail: str = "error") -> httpx.HTTPStatusError:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"detail": detail}
    response.text = detail
    return httpx.HTTPStatusError("", request=MagicMock(), response=response)


def _sample_finding() -> dict:
    return {
        "id": "find-001-uuid-1234",
        "subject": "python::no_bare_except::src/auth.py",
        "created_at": "2026-07-11T09:30:00",
        "payload": {
            "rule": "no_bare_except",
            "file": "src/auth.py",
            "message": "Bare except hides exceptions.",
        },
        "bundle": {
            "rule": {
                "id": "no_bare_except",
                "in_registry": True,
                "rationale": "Catching all exceptions prevents targeted error handling.",
            },
            "remediation": {
                "description": "Replace bare except with specific exception types.",
                "status": "active",
            },
        },
    }


def _make_lane_client() -> AsyncMock:
    lane = AsyncMock()
    lane.list_delegated.return_value = {"findings": [], "count": 0}
    lane.claim.return_value = None
    lane.next_delegated.return_value = _sample_finding()

    client = AsyncMock()
    client.lane = lane
    return client


# ---------------------------------------------------------------------------
# list_delegated
# ---------------------------------------------------------------------------


async def test_list_delegated_empty() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.list_delegated.return_value = {"findings": [], "count": 0}

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_delegated.__wrapped__(limit=20, full_ids=False)

    mock_client.lane.list_delegated.assert_called_once_with(limit=20)


async def test_list_delegated_with_items() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.list_delegated.return_value = {
        "findings": [_sample_finding()],
        "count": 1,
    }

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_delegated.__wrapped__(limit=20, full_ids=False)

    mock_client.lane.list_delegated.assert_called_once_with(limit=20)


async def test_list_delegated_with_full_ids() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.list_delegated.return_value = {
        "findings": [_sample_finding()],
        "count": 1,
    }

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_delegated.__wrapped__(limit=5, full_ids=True)

    mock_client.lane.list_delegated.assert_called_once_with(limit=5)


# ---------------------------------------------------------------------------
# claim
# ---------------------------------------------------------------------------


async def test_claim_success() -> None:
    mock_client = _make_lane_client()

    with patch(_CLAIM_CLIENT, return_value=mock_client):
        await claim.__wrapped__(finding_id="find-001-uuid-1234", agent="claude-code")

    mock_client.lane.claim.assert_called_once_with(
        "find-001-uuid-1234", agent="claude-code"
    )


async def test_claim_not_found_raises_exit() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.claim.side_effect = _http_error(404)

    with patch(_CLAIM_CLIENT, return_value=mock_client):
        with pytest.raises(typer.Exit) as exc_info:
            await claim.__wrapped__(finding_id="missing-id", agent="claude-code")

    assert exc_info.value.exit_code == 1


async def test_claim_non_404_propagates() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.claim.side_effect = _http_error(500)

    with patch(_CLAIM_CLIENT, return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await claim.__wrapped__(finding_id="find-001-uuid-1234", agent="claude-code")


# ---------------------------------------------------------------------------
# next_finding
# ---------------------------------------------------------------------------


async def test_next_finding_empty_lane() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.next_delegated.side_effect = _http_error(404)

    with patch(_NEXT_CLIENT, return_value=mock_client):
        # 404 → prints "Lane is empty" and returns cleanly (no Exit raised)
        await next_finding.__wrapped__()

    mock_client.lane.next_delegated.assert_called_once()


async def test_next_finding_returns_finding() -> None:
    mock_client = _make_lane_client()

    with patch(_NEXT_CLIENT, return_value=mock_client):
        await next_finding.__wrapped__()

    mock_client.lane.next_delegated.assert_called_once()


async def test_next_finding_with_retired_rule_warning() -> None:
    mock_client = _make_lane_client()
    finding = _sample_finding()
    finding["bundle"]["rule"]["in_registry"] = False
    mock_client.lane.next_delegated.return_value = finding

    with patch(_NEXT_CLIENT, return_value=mock_client):
        await next_finding.__wrapped__()

    mock_client.lane.next_delegated.assert_called_once()


async def test_next_finding_non_404_propagates() -> None:
    mock_client = _make_lane_client()
    mock_client.lane.next_delegated.side_effect = _http_error(503)

    with patch(_NEXT_CLIENT, return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await next_finding.__wrapped__()
