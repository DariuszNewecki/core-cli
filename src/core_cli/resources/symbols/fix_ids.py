# src/core_cli/resources/symbols/fix_ids.py

"""Assign stable # ID: anchors to untagged symbols — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("fix-ids")
@core_command(dangerous=True, requires_context=False, confirmation=True)
# ID: 37ac33b4-76d3-40c4-8955-3b81a2a4ccf2
async def fix_ids_command(
    ctx: typer.Context,
    write: bool = typer.Option(
        False, "--write", help="Inject missing UUIDs into source files."
    ),
) -> None:
    """Assign stable '# ID:' anchors to all untagged public symbols.

    Scans 'src/' and modifies files to ensure knowledge graph stability.
    Pass --write to apply changes (default is dry-run).
    """
    mode = "WRITE" if write else "DRY-RUN"
    console.print(f"[bold cyan]Fixing symbol IDs ({mode})...[/bold cyan]")
    client = CoreApiClient()
    result = await client.fix.run_fix("fix.ids", write=write)
    run_id = result.get("run_id")
    console.print(f"[green]Dispatched fix.ids run {run_id}.[/green]")
    console.print(f"[dim]Poll with: core-admin fix status {run_id}[/dim]")
