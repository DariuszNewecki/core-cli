"""Consumer symbol-registry commands."""

from __future__ import annotations

from . import (  # noqa: F401
    audit,
    fix_ids,
    resolve_duplicates,
)
from .hub import app


__all__ = ["app"]
