# src/cli/resources/proposals/__init__.py
"""A3 Autonomous Proposal management."""

from __future__ import annotations

import typer

from . import create, integrate, manage
from . import list as list_mod


app = typer.Typer(
    name="proposals",
    help="Operations for the A3 Autonomous Proposal system (propose, approve, execute).",
    no_args_is_help=True,
)


# Register actions
app.command("list")(list_mod.list_proposals)
app.command("create")(create.create_proposal)
app.command("show")(manage.show_proposal)
app.command("approve")(manage.approve_proposal)
app.command("reject")(manage.reject_proposal)
app.command("execute")(manage.execute_proposal)
app.command("integrate")(integrate.integrate_cmd)

__all__ = ["app"]
