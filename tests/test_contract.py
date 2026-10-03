"""core-cli speaks only CORE's published API contract.

Every HTTP call core-cli makes goes through ``CoreApiClient._request`` in
``core_cli/client.py``. This test reads each of those calls straight from the
source and checks that its method and path are in CORE's committed OpenAPI
document (``docs/reference/openapi.json`` in the CORE repository, ADR-087 D9).

Where the contract comes from, first match wins:

1. ``CORE_OPENAPI_SPEC`` — a file path or an http(s) URL;
2. a CORE checkout next to this repository (``../CORE``);
3. CORE's ``main`` branch on GitHub.
"""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "src" / "core_cli" / "client.py"
SIBLING_SPEC = ROOT.parent / "CORE" / "docs" / "reference" / "openapi.json"
MAIN_SPEC_URL = (
    "https://raw.githubusercontent.com/DariuszNewecki/CORE/main/"
    "docs/reference/openapi.json"
)
_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _load_spec() -> dict:
    source = os.environ.get("CORE_OPENAPI_SPEC")
    if source is None and SIBLING_SPEC.exists():
        source = str(SIBLING_SPEC)
    source = source or MAIN_SPEC_URL
    if source.startswith(("http://", "https://")):
        response = httpx.get(source, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _template(node: ast.expr) -> str:
    """A path literal, with f-string fields normalised to ``{}``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            else:
                parts.append("{}")
        return "".join(parts)
    raise AssertionError(f"line {node.lineno}: path is not a literal")


def _client_calls() -> list[tuple[str, str, int]]:
    calls = []
    for node in ast.walk(ast.parse(CLIENT.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_request"
            and len(node.args) >= 2
        ):
            method = node.args[0]
            assert isinstance(method, ast.Constant), f"line {node.lineno}"
            calls.append(
                (str(method.value).upper(), _template(node.args[1]), node.lineno)
            )
    return calls


def _normalise(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


@pytest.fixture(scope="module")
def contract() -> set[tuple[str, str]]:
    spec = _load_spec()
    return {
        (method.upper(), _normalise(path))
        for path, operations in spec["paths"].items()
        for method in operations
        if method in _HTTP_METHODS
    }


def test_client_calls_are_found() -> None:
    # Guards the parser: the client makes well over a dozen distinct calls.
    assert len(_client_calls()) >= 20


@pytest.mark.parametrize(
    ("method", "path", "line"), _client_calls(), ids=lambda v: str(v)
)
def test_call_is_in_the_contract(
    contract: set[tuple[str, str]], method: str, path: str, line: int
) -> None:
    assert (method, _normalise(path)) in contract, (
        f"client.py:{line} calls {method} {path}, which CORE's OpenAPI contract "
        "does not publish"
    )


def test_commands_make_no_http_calls_of_their_own() -> None:
    """Only client.py talks HTTP; command modules go through CoreApiClient."""
    offenders = []
    for path in (ROOT / "src" / "core_cli").rglob("*.py"):
        if path == CLIENT:
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(
            r"httpx\.(AsyncClient|Client|get|post|put|patch|delete|request)\b", source
        ):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
