# src/core_cli/resources/symbols/sync.py

"""Synchronize filesystem symbols with the DB — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("sync")
@core_command(dangerous=True, requires_context=False)
# ID: 7de43597-32ac-4e0f-9e55-af90f4c716f6
async def sync_symbols(
    ctx: typer.Context,
    write: bool = typer.Option(
        False, "--write", help="Apply synchronization to the database."
    ),
) -> None:
    """Synchronize filesystem symbols with the PostgreSQL Knowledge Graph.

    Scans 'src/' and updates the 'core.symbols' table.
    Pass --write to apply changes (default is dry-run).
    """
    mode = "WRITE" if write else "DRY-RUN"
    console.print(f"[bold cyan]Synchronizing Symbols to DB ({mode})...[/bold cyan]")
    client = CoreApiClient()
    result = await client.fix.run_fix("sync.db", write=write)
    run_id = result.get("run_id")
    console.print(f"[green]Dispatched sync.db run {run_id}.[/green]")
    console.print(f"[dim]Poll with: core-admin fix status {run_id}[/dim]")
