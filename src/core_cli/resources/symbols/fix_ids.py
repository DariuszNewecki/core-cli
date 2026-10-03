# src/core_cli/resources/symbols/fix_ids.py

"""Assign stable # ID: anchors to untagged symbols — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("fix-ids")
@core_command(dangerous=True, confirmation=True)
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
    result = await client.run_fix("fix.ids", write=write)
    run_id = result.get("run_id")
    if not run_id:
        console.print(f"[red]fix.ids failed to dispatch: {result}[/red]")
        raise typer.Exit(1)
    final = await client._poll_run(run_id)
    if final.get("status") != "completed":
        console.print(f"[red]fix.ids failed: {final.get('error') or final}[/red]")
        raise typer.Exit(1)
    console.print("[green]✓ fix.ids completed.[/green]")
