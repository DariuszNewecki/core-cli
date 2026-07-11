# tests/test_code.py

"""Unit tests for code/* CLI commands — stub the HTTP client layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core_cli.resources.code.audit_duplicates import audit_duplicates_cmd
from core_cli.resources.code.bridges import list_bridges_cmd
from core_cli.resources.code.check_ui import check_ui_cmd
from core_cli.resources.code.docstrings import fix_docstrings_command
from core_cli.resources.code.format import format_command, format_imports_cmd
from core_cli.resources.code.test import test_command

# Patch targets: where CoreApiClient is imported in each module.
_AUDIT_CLIENT = "core_cli.resources.code.audit_duplicates.CoreApiClient"
_BRIDGES_CLIENT = "core_cli.resources.code.bridges.CoreApiClient"
_CHECK_UI_CLIENT = "core_cli.resources.code.check_ui.CoreApiClient"
_DOCSTRINGS_CLIENT = "core_cli.resources.code.docstrings.CoreApiClient"
_FORMAT_CLIENT = "core_cli.resources.code.format.CoreApiClient"
_TEST_CLIENT = "core_cli.resources.code.test.CoreApiClient"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_error(status_code: int, detail: str = "error") -> httpx.HTTPStatusError:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"detail": detail}
    response.text = detail
    return httpx.HTTPStatusError("", request=MagicMock(), response=response)


def _make_async_client() -> AsyncMock:
    client = AsyncMock()
    # inspect sub-client
    client.inspect = AsyncMock()
    client.inspect.analysis_duplicates.return_value = {
        "ok": True,
        "threshold": 0.96,
        "note": "results emitted to logs",
    }
    client.inspect.analysis_bridges.return_value = {
        "available": True,
        "count": 0,
        "consuming": None,
        "bridges": [],
    }
    # run_fix / _poll_run for fix-based commands
    client.run_fix.return_value = {"run_id": "run-abc-123"}
    client._poll_run.return_value = {"status": "completed"}
    # quality endpoints
    client.quality_body_ui.return_value = {"status": "ok", "violations": []}
    client.quality_tests.return_value = {"run_id": "run-test-001"}
    return client


def _sample_bridge() -> dict:
    return {
        "id": "bridge.audit.finding.to.blackboard",
        "title": "AuditFinding → Blackboard",
        "description": "AuditFindings are posted to the blackboard for remediation.",
        "bridge_class": "AuditFinding",
        "bridge_layer": "Body",
        "source_layer": "Mind",
        "source_context": "mind.ast_gate produces AuditFinding objects",
        "consuming_types": ["AuditFinding"],
        "sink_target": "blackboard_entries",
        "sink_layer": "Body",
        "sink_via": "Worker.post_finding()",
        "attribution_mechanism": "worker_uuid",
        "attribution_field": "worker_uuid",
        "attribution_note": None,
        "authority_adrs": ["ADR-021", "ADR-041"],
    }


# ---------------------------------------------------------------------------
# audit_duplicates_cmd
# ---------------------------------------------------------------------------


async def test_audit_duplicates_success() -> None:
    mock_client = _make_async_client()

    with patch(_AUDIT_CLIENT, return_value=mock_client):
        await audit_duplicates_cmd.__wrapped__(threshold=0.96)

    mock_client.inspect.analysis_duplicates.assert_called_once_with(threshold=0.96)


async def test_audit_duplicates_custom_threshold() -> None:
    mock_client = _make_async_client()
    mock_client.inspect.analysis_duplicates.return_value = {
        "ok": True,
        "threshold": 0.75,
        "note": "results emitted to logs",
    }

    with patch(_AUDIT_CLIENT, return_value=mock_client):
        await audit_duplicates_cmd.__wrapped__(threshold=0.75)

    mock_client.inspect.analysis_duplicates.assert_called_once_with(threshold=0.75)


async def test_audit_duplicates_failure_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client.inspect.analysis_duplicates.return_value = {
        "ok": False,
        "error": "qdrant_service not configured",
    }

    with patch(_AUDIT_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await audit_duplicates_cmd.__wrapped__(threshold=0.96)


# ---------------------------------------------------------------------------
# list_bridges_cmd
# ---------------------------------------------------------------------------


async def test_list_bridges_empty() -> None:
    mock_client = _make_async_client()

    with patch(_BRIDGES_CLIENT, return_value=mock_client):
        await list_bridges_cmd.__wrapped__(consuming=None)

    mock_client.inspect.analysis_bridges.assert_called_once_with(consuming=None)


async def test_list_bridges_with_results() -> None:
    mock_client = _make_async_client()
    mock_client.inspect.analysis_bridges.return_value = {
        "available": True,
        "count": 1,
        "consuming": None,
        "bridges": [_sample_bridge()],
    }

    with patch(_BRIDGES_CLIENT, return_value=mock_client):
        await list_bridges_cmd.__wrapped__(consuming=None)

    mock_client.inspect.analysis_bridges.assert_called_once_with(consuming=None)


async def test_list_bridges_with_consuming_filter() -> None:
    mock_client = _make_async_client()
    mock_client.inspect.analysis_bridges.return_value = {
        "available": True,
        "count": 1,
        "consuming": "AuditFinding",
        "bridges": [_sample_bridge()],
    }

    with patch(_BRIDGES_CLIENT, return_value=mock_client):
        await list_bridges_cmd.__wrapped__(consuming="AuditFinding")

    mock_client.inspect.analysis_bridges.assert_called_once_with(
        consuming="AuditFinding"
    )


async def test_list_bridges_unavailable_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client.inspect.analysis_bridges.return_value = {
        "available": False,
        "error": "IntentRepository not initialized",
        "bridges": [],
    }

    with patch(_BRIDGES_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await list_bridges_cmd.__wrapped__(consuming=None)


# ---------------------------------------------------------------------------
# check_ui_cmd
# ---------------------------------------------------------------------------


async def test_check_ui_clean() -> None:
    mock_client = _make_async_client()

    with patch(_CHECK_UI_CLIENT, return_value=mock_client):
        await check_ui_cmd.__wrapped__(write=False)

    mock_client.quality_body_ui.assert_called_once()


async def test_check_ui_violations_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client.quality_body_ui.return_value = {
        "status": "violations",
        "violations": [{"file": "src/body/foo.py", "line": 42, "type": "print"}],
    }

    with patch(_CHECK_UI_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await check_ui_cmd.__wrapped__(write=False)


async def test_check_ui_write_dispatches_fix() -> None:
    mock_client = _make_async_client()

    with patch(_CHECK_UI_CLIENT, return_value=mock_client):
        await check_ui_cmd.__wrapped__(write=True)

    mock_client.run_fix.assert_called_once_with("fix.body_ui", write=True)
    mock_client._poll_run.assert_called_once_with("run-abc-123")


async def test_check_ui_write_fix_fails_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client._poll_run.return_value = {"status": "failed", "error": "boom"}

    with patch(_CHECK_UI_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await check_ui_cmd.__wrapped__(write=True)


# ---------------------------------------------------------------------------
# fix_docstrings_command
# ---------------------------------------------------------------------------


async def test_docstrings_dry_run() -> None:
    mock_client = _make_async_client()

    with patch(_DOCSTRINGS_CLIENT, return_value=mock_client):
        await fix_docstrings_command.__wrapped__(write=False, limit=3, file=None)

    mock_client.run_fix.assert_called_once_with(
        "fix.docstrings",
        target_files=None,
        write=False,
        params={"limit": 3},
    )


async def test_docstrings_write_with_file() -> None:
    mock_client = _make_async_client()

    with patch(_DOCSTRINGS_CLIENT, return_value=mock_client):
        await fix_docstrings_command.__wrapped__(
            write=True, limit=5, file="src/body/foo.py"
        )

    call_kwargs = mock_client.run_fix.call_args.kwargs
    assert call_kwargs["target_files"] == ["src/body/foo.py"]
    assert call_kwargs["write"] is True
    assert call_kwargs["params"]["limit"] == 5


async def test_docstrings_no_run_id_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client.run_fix.return_value = {}

    with patch(_DOCSTRINGS_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await fix_docstrings_command.__wrapped__(write=False, limit=3, file=None)


# ---------------------------------------------------------------------------
# format_command / format_imports_cmd
# ---------------------------------------------------------------------------


async def test_format_dry_run() -> None:
    mock_client = _make_async_client()

    with patch(_FORMAT_CLIENT, return_value=mock_client):
        await format_command.__wrapped__(write=False)

    mock_client.run_fix.assert_called_once_with("fix.format", write=False)


async def test_format_write() -> None:
    mock_client = _make_async_client()

    with patch(_FORMAT_CLIENT, return_value=mock_client):
        await format_command.__wrapped__(write=True)

    mock_client.run_fix.assert_called_once_with("fix.format", write=True)


async def test_format_imports() -> None:
    mock_client = _make_async_client()

    with patch(_FORMAT_CLIENT, return_value=mock_client):
        await format_imports_cmd.__wrapped__(write=False)

    mock_client.run_fix.assert_called_once_with("fix.imports", write=False)


async def test_format_poll_failure_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client._poll_run.return_value = {"status": "failed", "error": "timeout"}

    with patch(_FORMAT_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await format_command.__wrapped__(write=False)


# ---------------------------------------------------------------------------
# test_command
# ---------------------------------------------------------------------------


async def test_test_command_success() -> None:
    mock_client = _make_async_client()

    with patch(_TEST_CLIENT, return_value=mock_client):
        await test_command.__wrapped__()

    mock_client.quality_tests.assert_called_once()
    mock_client._poll_run.assert_called_once_with("run-test-001")


async def test_test_command_no_run_id_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client.quality_tests.return_value = {}

    with patch(_TEST_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await test_command.__wrapped__()


async def test_test_command_poll_failure_raises_exit() -> None:
    mock_client = _make_async_client()
    mock_client._poll_run.return_value = {"status": "failed", "error": "test runner crashed"}

    with patch(_TEST_CLIENT, return_value=mock_client):
        with pytest.raises(SystemExit):
            await test_command.__wrapped__()
