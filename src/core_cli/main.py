"""core-cli entry point — consumer governance CLI."""

from __future__ import annotations

import typer

from core_cli.resources.code import app as code_app
from core_cli.resources.lane import app as lane_app
from core_cli.resources.project import app as project_app
from core_cli.resources.proposals import app as proposals_app
from core_cli.resources.symbols import app as symbols_app
from core_cli.resources.vectors import app as vectors_app


# ID: 92ffef66-e5d7-48ae-929e-a82f136a9719
app = typer.Typer(
    name="core",
    help="CORE consumer governance CLI — govern your project against CORE constitutional rules.",
    no_args_is_help=True,
)

app.add_typer(lane_app, name="lane")
app.add_typer(proposals_app, name="proposals")
app.add_typer(code_app, name="code")
app.add_typer(symbols_app, name="symbols")
app.add_typer(vectors_app, name="vectors")
app.add_typer(project_app, name="project")


if __name__ == "__main__":
    app()
