# src/core_cli/resources/symbols/resolve_duplicates.py

"""Resolve duplicate symbol IDs — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("resolve-duplicates")
@core_command(dangerous=True, requires_context=False, confirmation=True)
# ID: c9ca3aa7-a542-4f3c-bbf3-d8dc97d4400a
async def resolve_symbol_duplicates(
    ctx: typer.Context,
    write: bool = typer.Option(False, "--write", help="Regenerate conflicting UUIDs."),
) -> None:
    """Find and resolve duplicate '# ID:' anchors in the codebase.

    The older entry is preserved; colliding symbols receive fresh identifiers.
    Pass --write to apply changes (default is dry-run).
    """
    mode = "RESOLVING" if write else "ANALYZING"
    console.print(f"[bold cyan]{mode} duplicate ID collisions...[/bold cyan]")
    client = CoreApiClient()
    result = await client.fix.run_fix("fix.duplicate_ids", write=write)
    run_id = result.get("run_id")
    console.print(f"[green]Dispatched fix.duplicate_ids run {run_id}.[/green]")
    console.print(f"[dim]Poll with: core-admin fix status {run_id}[/dim]")
