# tests/test_proposals.py

"""Unit tests for proposals CLI commands — stub the HTTP client layer."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import typer

from core_cli.resources.proposals.create import create_proposal
from core_cli.resources.proposals.list import list_proposals
from core_cli.resources.proposals.manage import (
    approve_proposal,
    execute_proposal,
    reject_proposal,
    show_proposal,
)

# Patch targets: where CoreApiClient is imported in each module.
_LIST_CLIENT = "core_cli.resources.proposals.list.CoreApiClient"
_MANAGE_CLIENT = "core_cli.resources.proposals.manage.CoreApiClient"
_CREATE_CLIENT = "core_cli.resources.proposals.create.CoreApiClient"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_error(status_code: int, detail: str = "error") -> httpx.HTTPStatusError:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"detail": detail}
    response.text = detail
    return httpx.HTTPStatusError("", request=MagicMock(), response=response)


def _sample_proposal() -> dict:
    return {
        "proposal_id": "abc123def456789",
        "goal": "Fix the authentication bug",
        "status": "pending",
        "created_at": "2026-07-11T10:00:00",
        "created_by": "test_agent",
        "risk": {"overall_risk": "safe", "risk_factors": []},
        "approval_required": False,
        "actions": [{"action_id": "fix.auth", "order": 0, "parameters": {}}],
        "scope": {"files": ["src/auth.py"], "modules": []},
    }


def _make_client(**overrides) -> AsyncMock:
    client = AsyncMock()
    client.list_proposals.return_value = {"proposals": []}
    client.get_proposal.return_value = _sample_proposal()
    client.approve_proposal.return_value = {
        "approved_by": "cli_admin",
        "approval_authority": "principal.governor",
    }
    client.execute_proposal.return_value = {
        "ok": True,
        "actions_executed": 1,
        "actions_succeeded": 1,
        "actions_failed": 0,
        "duration_sec": 0.5,
        "action_results": {"fix.auth": {"ok": True, "duration_sec": 0.4}},
    }
    client.reject_proposal.return_value = {
        "proposal_id": "abc123def456789",
        "revived_count": 0,
    }
    client.create_proposal.return_value = {
        "proposal": {
            "proposal_id": "new-proposal-id",
            "goal": "Fix the auth bug",
            "risk": {"overall_risk": "safe"},
        }
    }
    for k, v in overrides.items():
        setattr(client, k, v)
    return client


# ---------------------------------------------------------------------------
# list_proposals
# ---------------------------------------------------------------------------


async def test_list_proposals_empty() -> None:
    mock_client = _make_client()
    mock_client.list_proposals.return_value = {"proposals": []}

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_proposals.__wrapped__(status=None, limit=20, full_ids=False)

    mock_client.list_proposals.assert_called_once_with(status=None, limit=20)


async def test_list_proposals_with_items() -> None:
    mock_client = _make_client()
    mock_client.list_proposals.return_value = {"proposals": [_sample_proposal()]}

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_proposals.__wrapped__(status=None, limit=20, full_ids=False)

    mock_client.list_proposals.assert_called_once_with(status=None, limit=20)


async def test_list_proposals_full_ids() -> None:
    mock_client = _make_client()
    mock_client.list_proposals.return_value = {"proposals": [_sample_proposal()]}

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_proposals.__wrapped__(status=None, limit=5, full_ids=True)

    mock_client.list_proposals.assert_called_once_with(status=None, limit=5)


async def test_list_proposals_invalid_status_returns() -> None:
    mock_client = _make_client()
    mock_client.list_proposals.side_effect = _http_error(400, "Invalid status")

    with patch(_LIST_CLIENT, return_value=mock_client):
        # 400 → prints error and returns cleanly (no exception propagates)
        await list_proposals.__wrapped__(status="bogus", limit=20, full_ids=False)


async def test_list_proposals_filters_by_status() -> None:
    mock_client = _make_client()
    mock_client.list_proposals.return_value = {"proposals": []}

    with patch(_LIST_CLIENT, return_value=mock_client):
        await list_proposals.__wrapped__(status="approved", limit=10, full_ids=False)

    mock_client.list_proposals.assert_called_once_with(status="approved", limit=10)


# ---------------------------------------------------------------------------
# show_proposal
# ---------------------------------------------------------------------------


async def test_show_proposal_happy_path() -> None:
    mock_client = _make_client()

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await show_proposal.__wrapped__(proposal_id="abc123")

    mock_client.get_proposal.assert_called_once_with("abc123")


async def test_show_proposal_not_found() -> None:
    mock_client = _make_client()
    mock_client.get_proposal.side_effect = _http_error(404)

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        with pytest.raises(typer.Exit) as exc_info:
            await show_proposal.__wrapped__(proposal_id="missing")

    assert exc_info.value.exit_code == 1


# ---------------------------------------------------------------------------
# approve_proposal
# ---------------------------------------------------------------------------


@contextmanager
def _terminal(typed: str | None = "abc123de", tty: bool = True):
    """A person at a real terminal typing *typed* (CORE ADR-168 R2)."""
    stdin = MagicMock()
    stdin.isatty.return_value = tty
    with (
        patch("core_cli.resources.proposals.manage.sys.stdin", stdin),
        patch(
            "core_cli.resources.proposals.manage.typer.prompt", return_value=typed
        ) as prompt,
    ):
        yield prompt


async def _approve(mock_client: AsyncMock, proposal_id: str = "abc123") -> None:
    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await approve_proposal.__wrapped__(
            proposal_id=proposal_id,
            by="cli_admin",
            authority="principal.governor",
        )


async def test_approve_proposal_success() -> None:
    mock_client = _make_client()

    with _terminal() as prompt:
        await _approve(mock_client)

    assert "abc123de" in prompt.call_args.args[0]
    mock_client.approve_proposal.assert_called_once_with(
        "abc123",
        approved_by="cli_admin",
        approval_authority="principal.governor",
    )


async def test_approve_refused_without_a_terminal() -> None:
    """A session with no terminal (e.g. a model's shell) cannot approve."""
    mock_client = _make_client()

    with _terminal(tty=False) as prompt, pytest.raises(typer.Exit) as exc_info:
        await _approve(mock_client)

    assert exc_info.value.exit_code == 1
    prompt.assert_not_called()
    mock_client.approve_proposal.assert_not_called()


async def test_approve_refused_when_the_typed_id_does_not_match() -> None:
    mock_client = _make_client()

    with _terminal(typed="yes"), pytest.raises(typer.Exit):
        await _approve(mock_client)

    mock_client.approve_proposal.assert_not_called()


async def test_approve_proposal_not_found() -> None:
    mock_client = _make_client()
    mock_client.get_proposal.side_effect = _http_error(404)

    with _terminal(), pytest.raises(typer.Exit) as exc_info:
        await _approve(mock_client, "missing")

    assert exc_info.value.exit_code == 1
    mock_client.approve_proposal.assert_not_called()


async def test_approve_proposal_bad_request_prints_detail() -> None:
    mock_client = _make_client()
    mock_client.approve_proposal.side_effect = _http_error(400, "already approved")

    with _terminal(), pytest.raises(typer.Exit) as exc_info:
        await _approve(mock_client)

    assert exc_info.value.exit_code == 1


async def test_show_renders_who_why_and_step_zero(capsys) -> None:
    proposal = _sample_proposal()
    proposal["validation_results"] = {"full_audit": True, "tests": False}
    proposal["constitutional_constraints"] = {
        "provenance": {
            "anchor_kind": "governor_request",
            "anchor_refs": ["add a status line"],
            "problem_owner": "governor",
            "producer": "claude-session:core-darek",
            "retires": ["src/old.py"],
        },
        "step_zero": {
            "retires": [
                {
                    "entry": "src/old.py",
                    "verified": True,
                    "reason": "deleted by the patch",
                }
            ],
            "look_alikes": {"status": "unavailable", "reason": "qdrant down"},
            "decisions": {
                "mentions": {"src/old.py": [{"id": "ADR-005", "status": "accepted"}]},
                "history": {"src/old.py": None},
            },
        },
    }
    mock_client = _make_client()
    mock_client.get_proposal.return_value = proposal

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await show_proposal.__wrapped__(proposal_id="abc123")

    out = capsys.readouterr().out
    for text in (
        "add a status line",
        "claude-session:core-darek",
        "deleted by the patch",
        "full_audit",
        "not searched: qdrant down",
        "ADR-005 (accepted)",
        "history unreadable",
    ):
        assert text in out, text


# ---------------------------------------------------------------------------
# execute_proposal
# ---------------------------------------------------------------------------


async def test_execute_proposal_dry_run() -> None:
    mock_client = _make_client()

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await execute_proposal.__wrapped__(proposal_id="abc123", write=False)

    mock_client.execute_proposal.assert_called_once_with("abc123", write=False)


async def test_execute_proposal_write_success() -> None:
    mock_client = _make_client()

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await execute_proposal.__wrapped__(proposal_id="abc123", write=True)

    mock_client.execute_proposal.assert_called_once_with("abc123", write=True)


async def test_execute_proposal_failure_response() -> None:
    mock_client = _make_client()
    mock_client.execute_proposal.return_value = {
        "ok": False,
        "actions_executed": 1,
        "actions_succeeded": 0,
        "actions_failed": 1,
        "duration_sec": 0.1,
        "action_results": {
            "fix.auth": {"ok": False, "duration_sec": 0.1, "data": {"error": "boom"}}
        },
    }

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await execute_proposal.__wrapped__(proposal_id="abc123", write=True)

    mock_client.execute_proposal.assert_called_once_with("abc123", write=True)


# ---------------------------------------------------------------------------
# reject_proposal
# ---------------------------------------------------------------------------


async def test_reject_proposal_success() -> None:
    mock_client = _make_client()

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await reject_proposal.__wrapped__(proposal_id="abc123", reason="out of scope")

    mock_client.reject_proposal.assert_called_once_with("abc123", reason="out of scope")


async def test_reject_proposal_with_revived_findings() -> None:
    mock_client = _make_client()
    mock_client.reject_proposal.return_value = {
        "proposal_id": "abc123def456789",
        "revived_count": 3,
    }

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        await reject_proposal.__wrapped__(proposal_id="abc123", reason="stale")

    mock_client.reject_proposal.assert_called_once_with("abc123", reason="stale")


async def test_reject_proposal_not_found() -> None:
    mock_client = _make_client()
    mock_client.reject_proposal.side_effect = _http_error(404)

    with patch(_MANAGE_CLIENT, return_value=mock_client):
        with pytest.raises(typer.Exit) as exc_info:
            await reject_proposal.__wrapped__(proposal_id="missing", reason="n/a")

    assert exc_info.value.exit_code == 1


# ---------------------------------------------------------------------------
# create_proposal
# ---------------------------------------------------------------------------


async def test_create_proposal_dry_run() -> None:
    mock_client = _make_client()

    with patch(_CREATE_CLIENT, return_value=mock_client):
        await create_proposal.__wrapped__(
            goal="Fix the auth bug",
            actions=[],
            files=[],
            write=False,
        )

    mock_client.create_proposal.assert_called_once()
    call_kwargs = mock_client.create_proposal.call_args.kwargs
    assert call_kwargs["goal"] == "Fix the auth bug"
    assert call_kwargs["write"] is False


async def test_create_proposal_write() -> None:
    mock_client = _make_client()

    with patch(_CREATE_CLIENT, return_value=mock_client):
        await create_proposal.__wrapped__(
            goal="Fix the auth bug",
            actions=["fix.auth:file=src/auth.py"],
            files=["src/auth.py"],
            write=True,
        )

    call_kwargs = mock_client.create_proposal.call_args.kwargs
    assert call_kwargs["write"] is True
    assert len(call_kwargs["actions"]) == 1
    assert call_kwargs["actions"][0]["action_id"] == "fix.auth"


async def test_create_proposal_http_error() -> None:
    mock_client = _make_client()
    mock_client.create_proposal.side_effect = _http_error(400, "Bad goal")

    with patch(_CREATE_CLIENT, return_value=mock_client):
        with pytest.raises(typer.Exit) as exc_info:
            await create_proposal.__wrapped__(
                goal="",
                actions=[],
                files=[],
                write=True,
            )

    assert exc_info.value.exit_code == 1
