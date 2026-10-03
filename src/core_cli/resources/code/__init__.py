"""Consumer codebase commands — quality, style, and verification over HTTP."""

from __future__ import annotations

from . import (  # noqa: F401
    actions,
    audit_duplicates,
    bridges,
    check_imports,
    docstrings,
    fix_atomic,
    format,
    integrity,
    lint,
    logging,
    test,
)
from .hub import app


__all__ = ["app"]
