"""Consumer project lifecycle commands."""

from __future__ import annotations

import typer


app = typer.Typer(
    name="project",
    help="Operations for project lifecycle: onboarding and documentation.",
    no_args_is_help=True,
)

from . import (
    docs,
    onboard,
    scout,
)


__all__ = ["app"]
