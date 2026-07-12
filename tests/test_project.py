# tests/test_project.py

"""Unit tests for project onboard/promote/scout — stub the HTTP client layer.

Covers the relative-path resolution fix: `path` is sent as a plain string
over HTTP and resolved by the CORE API process, not this CLI. A relative
path must be resolved to absolute here before it's ever sent, or it would
silently mean a different location depending on which process resolves it.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core_cli.resources.project.onboard import onboard_project, promote_onboard
from core_cli.resources.project.scout import scout_project


_ONBOARD_CLIENT = "core_cli.resources.project.onboard.CoreApiClient"
_SCOUT_CLIENT = "core_cli.resources.project.scout.CoreApiClient"


def _make_project_client(**overrides) -> AsyncMock:
    project = AsyncMock()
    project.onboard.return_value = {"mode": "write", "stage_dir": None}
    project.promote.return_value = {"promoted": True}
    project.scout.return_value = {"candidates": [], "candidate_count": 0, "matched": 0}
    for key, value in overrides.items():
        setattr(project, key, value)

    client = AsyncMock()
    client.project = project
    return client


# ---------------------------------------------------------------------------
# onboard_project
# ---------------------------------------------------------------------------


async def test_onboard_resolves_relative_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mock_client = _make_project_client()

    with patch(_ONBOARD_CLIENT, return_value=mock_client):
        await onboard_project.__wrapped__(
            ctx=MagicMock(), path=Path("."), write=True, stage=False
        )

    mock_client.project.onboard.assert_called_once_with(
        str(tmp_path), write=True, stage=False
    )


async def test_onboard_absolute_path_unchanged(tmp_path: Path) -> None:
    mock_client = _make_project_client()

    with patch(_ONBOARD_CLIENT, return_value=mock_client):
        await onboard_project.__wrapped__(
            ctx=MagicMock(), path=tmp_path, write=True, stage=False
        )

    mock_client.project.onboard.assert_called_once_with(
        str(tmp_path), write=True, stage=False
    )


# ---------------------------------------------------------------------------
# promote_onboard
# ---------------------------------------------------------------------------


async def test_promote_resolves_relative_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mock_client = _make_project_client()

    with patch(_ONBOARD_CLIENT, return_value=mock_client):
        await promote_onboard.__wrapped__(ctx=MagicMock(), path=Path("."))

    mock_client.project.promote.assert_called_once_with(str(tmp_path))


# ---------------------------------------------------------------------------
# scout_project
# ---------------------------------------------------------------------------


async def test_scout_resolves_relative_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mock_client = _make_project_client()

    with patch(_SCOUT_CLIENT, return_value=mock_client):
        await scout_project.__wrapped__(
            ctx=MagicMock(), path=Path("."), write=False, reset=False
        )

    mock_client.project.scout.assert_called_once_with(str(tmp_path), reset=False)
