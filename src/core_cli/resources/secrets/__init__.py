# src/cli/resources/secrets/__init__.py
"""Secrets resource hub."""

from __future__ import annotations

from . import manage  # noqa: F401
from .hub import app


__all__ = ["app"]
