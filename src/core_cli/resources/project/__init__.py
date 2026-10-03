"""Consumer project lifecycle commands."""

from __future__ import annotations

import typer


app = typer.Typer(
    name="project",
    help="Bring a repository under governance: scout, onboard, promote (BYOR).",
    no_args_is_help=True,
)

from . import (  # noqa: F401
    onboard,
    scout,
)


__all__ = ["app"]
