# src/core_cli/resources/project/docs.py

"""Generate capability reference documentation — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from . import app


console = Console()


@app.command("docs")
@core_command(dangerous=False, requires_context=False)
# ID: 6759f022-9e30-474c-8ea3-4740ee55249c
async def generate_project_docs(
    ctx: typer.Context,
    output: str = typer.Option(
        "docs/10_CAPABILITY_REFERENCE.md",
        "--output",
        "-o",
        help="Target path for the reference doc.",
    ),
) -> None:
    """Generate the canonical Capability Reference documentation.

    Extracts all public symbols and their intent from the database.
    """
    console.print(
        f"[bold cyan]Generating capability reference to:[/bold cyan] {output}"
    )
    client = CoreApiClient()
    result = await client.project.generate_docs(output=output)
    out = result.get("output", output)
    console.print(f"[green]Documentation updated: {out}[/green]")
