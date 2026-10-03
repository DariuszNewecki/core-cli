"""HTTP client for the CORE API — core-cli's only link to CORE.

core-cli talks to a running CORE over HTTP and nothing else: it has no
dependency on core-runtime (ADR-146, amended 2026-10-03). Every route called
here is in CORE's published OpenAPI contract, ``docs/reference/openapi.json``
in the CORE repository; ``tests/test_contract.py`` checks that.

The base URL comes from the ``CORE_API_URL`` environment variable, defaulting
to the loopback address CORE binds to.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
_TIMEOUT_SECONDS = 30.0
_LONG_TIMEOUT_SECONDS = 300.0
_POLL_INTERVAL_SECONDS = 1.0
_POLL_TERMINAL_STATES = frozenset({"completed", "failed"})


# ID: e5aeda69-d26e-4353-81eb-83e998e968e9
class CoreApiError(httpx.HTTPStatusError):
    """An error response (status >= 400) from the CORE API.

    An ``httpx.HTTPStatusError``, so commands can branch on
    ``exc.response.status_code``; ``status_code`` and ``detail`` (the API's
    ``detail`` field, or the raw body) are also set directly.
    """

    def __init__(self, response: httpx.Response) -> None:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        self.status_code = response.status_code
        self.detail = detail
        super().__init__(
            f"API error {response.status_code}: {detail}",
            request=response.request,
            response=response,
        )


# ID: 49ef4530-5b49-4ebb-a9f6-b59150780e1b
class CoreApiClient:
    """Async client for the CORE API.

    Methods mirror the API: flat methods for single routes, plus small
    namespaces (``inspect``, ``lane``, ``project``, ``symbols``, ``vectors``)
    for route families. A response with status >= 400 raises ``CoreApiError``.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.environ.get("CORE_API_URL") or DEFAULT_BASE_URL
        self.inspect = _Inspect(self)
        self.lane = _Lane(self)
        self.project = _Project(self)
        self.symbols = _Symbols(self)
        self.vectors = _Vectors(self)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: float = _TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> dict:
        async with httpx.AsyncClient(timeout=timeout) as http:
            response = await http.request(method, f"{self.base_url}{path}", **kwargs)
        if response.status_code >= 400:
            raise CoreApiError(response)
        return response.json()

    async def _poll_run(
        self, run_id: str, timeout_seconds: float = _LONG_TIMEOUT_SECONDS
    ) -> dict:
        """Poll GET /v1/fix/runs/{run_id} until the run completes or fails."""
        async with asyncio.timeout(timeout_seconds):
            while True:
                payload = await self._request("GET", f"/v1/fix/runs/{run_id}")
                if payload.get("status") in _POLL_TERMINAL_STATES:
                    return payload
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    # -- actions and fixes ----------------------------------------------

    # ID: d5e64d0c-4a5f-4518-96d2-d15388306f00
    async def list_actions(self) -> dict:
        """GET /v1/actions — list the registered atomic actions."""
        return await self._request("GET", "/v1/actions")

    # ID: 7a49a17d-66a0-413b-b76a-5044c399f109
    async def run_fix(
        self,
        fix_id: str,
        target_files: list[str] | None = None,
        write: bool = False,
        params: dict[str, Any] | None = None,
    ) -> dict:
        """POST /v1/fix/run/{fix_id} — dispatch a fix action; poll with _poll_run."""
        return await self._request(
            "POST",
            f"/v1/fix/run/{fix_id}",
            json={
                "target_files": target_files or [],
                "write": write,
                "params": params or {},
            },
        )

    # -- checks on the governed repository ------------------------------

    # ID: 80078450-7b0e-4a2e-b62c-b265d179aa74
    async def lint(self) -> dict:
        """POST /v1/lint — black --check and ruff check."""
        return await self._request("POST", "/v1/lint", timeout=_LONG_TIMEOUT_SECONDS)

    # ID: e07d0d0b-c466-4613-b63b-0df395730ba6
    async def quality_imports(self) -> dict:
        """POST /v1/quality/imports — import-resolution check."""
        return await self._request("POST", "/v1/quality/imports")

    # ID: 58ba647c-a7ce-4d58-966b-c21f55e7d3fe
    async def quality_tests(self, path: str | None = None) -> dict:
        """POST /v1/quality/tests — pytest, optionally scoped; poll with _poll_run."""
        return await self._request("POST", "/v1/quality/tests", json={"path": path})

    # ID: 2887d4f0-91a0-4db7-8df9-d33857113212
    async def baseline(self, label: str = "default") -> dict:
        """POST /v1/integrity/baseline — fingerprint src/."""
        return await self._request(
            "POST", "/v1/integrity/baseline", json={"label": label}
        )

    # ID: 7c860bc0-ec98-4a6f-9589-03c96bbe81b9
    async def verify(self, label: str = "default") -> dict:
        """POST /v1/integrity/verify — compare src/ against a baseline."""
        return await self._request(
            "POST", "/v1/integrity/verify", json={"label": label}
        )

    # ID: 2798cdc1-6743-4451-9c96-e6ecc2cb1d4e
    async def integrate(self, commit_message: str) -> dict:
        """POST /v1/integrate — stage, format/lint and commit the working tree."""
        return await self._request(
            "POST",
            "/v1/integrate",
            json={"commit_message": commit_message},
            timeout=_LONG_TIMEOUT_SECONDS,
        )

    # -- proposals --------------------------------------------------------

    # ID: 8bafbb59-8d23-45a5-8fc5-271b694bacbc
    async def list_proposals(self, status: str | None = None, limit: int = 50) -> dict:
        """GET /v1/proposals."""
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status
        return await self._request("GET", "/v1/proposals", params=params)

    # ID: 957be7d4-98b7-4e47-99d8-115921b3b12f
    async def create_proposal(
        self,
        goal: str,
        actions: list[dict] | None = None,
        files: list[str] | None = None,
        created_by: str = "cli_operator",
        write: bool = True,
    ) -> dict:
        """POST /v1/proposals."""
        return await self._request(
            "POST",
            "/v1/proposals",
            json={
                "goal": goal,
                "actions": actions or [],
                "files": files or [],
                "created_by": created_by,
                "write": write,
            },
        )

    # ID: 4c806d5c-fe6e-4ac9-a0cc-dae70a01af93
    async def get_proposal(self, proposal_id: str) -> dict:
        """GET /v1/proposals/{proposal_id}."""
        return await self._request("GET", f"/v1/proposals/{proposal_id}")

    # ID: b01d56fa-f71a-472d-aa2d-c68e420689f0
    async def approve_proposal(
        self, proposal_id: str, approved_by: str, approval_authority: str
    ) -> dict:
        """POST /v1/proposals/{proposal_id}/approve."""
        return await self._request(
            "POST",
            f"/v1/proposals/{proposal_id}/approve",
            json={"approved_by": approved_by, "approval_authority": approval_authority},
        )

    # ID: 0e5c0e42-34bd-44c0-848f-62a1c0f78037
    async def reject_proposal(self, proposal_id: str, reason: str) -> dict:
        """POST /v1/proposals/{proposal_id}/reject."""
        return await self._request(
            "POST", f"/v1/proposals/{proposal_id}/reject", json={"reason": reason}
        )

    # ID: bef4a752-8d94-4d20-89e3-fc1ba79899d9
    async def execute_proposal(self, proposal_id: str, write: bool = False) -> dict:
        """POST /v1/proposals/{proposal_id}/execute."""
        return await self._request(
            "POST", f"/v1/proposals/{proposal_id}/execute", json={"write": write}
        )


class _Namespace:
    def __init__(self, client: CoreApiClient) -> None:
        self._client = client


class _Inspect(_Namespace):
    async def analysis_duplicates(self, threshold: float = 0.85) -> dict:
        """GET /v1/analysis/duplicates."""
        return await self._client._request(
            "GET",
            "/v1/analysis/duplicates",
            params={"threshold": threshold},
            timeout=_LONG_TIMEOUT_SECONDS,
        )

    async def analysis_bridges(self, consuming: str | None = None) -> dict:
        """GET /v1/analysis/bridges."""
        params: dict[str, Any] = {}
        if consuming is not None:
            params["consuming"] = consuming
        return await self._client._request("GET", "/v1/analysis/bridges", params=params)


class _Lane(_Namespace):
    async def list_delegated(self, limit: int = 50) -> dict:
        """GET /v1/lane."""
        return await self._client._request("GET", "/v1/lane", params={"limit": limit})

    async def next_delegated(self) -> dict:
        """GET /v1/lane/next."""
        return await self._client._request("GET", "/v1/lane/next")

    async def get_delegated(self, finding_id: str) -> dict:
        """GET /v1/lane/{finding_id}."""
        return await self._client._request("GET", f"/v1/lane/{finding_id}")

    async def claim(self, finding_id: str, agent: str) -> dict:
        """POST /v1/lane/{finding_id}/claim."""
        return await self._client._request(
            "POST", f"/v1/lane/{finding_id}/claim", params={"agent": agent}
        )

    async def propose(
        self, finding_id: str, patch: str, validation_run_id: str
    ) -> dict:
        """POST /v1/lane/{finding_id}/propose."""
        return await self._client._request(
            "POST",
            f"/v1/lane/{finding_id}/propose",
            json={"patch": patch, "validation_run_id": validation_run_id},
        )


class _Project(_Namespace):
    async def scout(self, path: str, reset: bool = False) -> dict:
        """POST /v1/project/scout."""
        return await self._client._request(
            "POST", "/v1/project/scout", json={"path": path, "reset": reset}
        )

    async def onboard(
        self, path: str, write: bool = False, stage: bool = False
    ) -> dict:
        """POST /v1/project/onboard."""
        return await self._client._request(
            "POST",
            "/v1/project/onboard",
            json={"path": path, "write": write, "stage": stage},
        )

    async def promote(self, path: str) -> dict:
        """POST /v1/project/onboard/promote."""
        return await self._client._request(
            "POST", "/v1/project/onboard/promote", json={"path": path}
        )

    async def generate_docs(
        self, output: str = "docs/10_CAPABILITY_REFERENCE.md"
    ) -> dict:
        """POST /v1/project/docs."""
        return await self._client._request(
            "POST", "/v1/project/docs", json={"output": output}
        )


class _Symbols(_Namespace):
    async def get_unassigned(self) -> dict:
        """GET /v1/symbols/unassigned."""
        return await self._client._request("GET", "/v1/symbols/unassigned")

    async def get_drift(self) -> dict:
        """GET /v1/symbols/drift."""
        return await self._client._request("GET", "/v1/symbols/drift")


class _Vectors(_Namespace):
    async def query(
        self, query: str, collection: str = "policies", limit: int = 5
    ) -> dict:
        """POST /v1/vectors/query — semantic search over the governed repository."""
        return await self._client._request(
            "POST",
            "/v1/vectors/query",
            json={"query": query, "collection": collection, "limit": limit},
        )
