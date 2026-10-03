# src/core_cli/resources/symbols/resolve_duplicates.py

"""Resolve duplicate symbol IDs — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("resolve-duplicates")
@core_command(dangerous=True, confirmation=True)
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
    result = await client.run_fix("fix.duplicate_ids", write=write)
    run_id = result.get("run_id")
    if not run_id:
        console.print(f"[red]fix.duplicate_ids failed to dispatch: {result}[/red]")
        raise typer.Exit(1)
    final = await client._poll_run(run_id)
    if final.get("status") != "completed":
        console.print(
            f"[red]fix.duplicate_ids failed: {final.get('error') or final}[/red]"
        )
        raise typer.Exit(1)
    console.print("[green]✓ fix.duplicate_ids completed.[/green]")
