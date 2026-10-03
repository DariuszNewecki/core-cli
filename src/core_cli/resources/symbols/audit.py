# src/core_cli/resources/symbols/audit.py

"""Symbol audit command — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("audit")
@core_command(dangerous=False)
# ID: 2c32679a-ad9d-48e3-8cb0-b4cec7adea29
async def audit_symbols(ctx: typer.Context) -> None:
    """Audit symbol integrity: drift summary and unassigned ID report."""
    client = CoreApiClient()

    console.print("[bold cyan]1. Checking for Symbol Drift (Disk vs DB)...[/bold cyan]")
    drift = await client.symbols.get_drift()
    if not drift.get("available", True):
        console.print(f"[yellow]Drift data unavailable: {drift.get('error')}[/yellow]")
    else:
        violations = drift.get("anchor_violations", 0)
        pending = drift.get("pending_symbols", 0)
        last_sync = drift.get("last_sync_at") or "never"
        if violations == 0 and pending == 0:
            console.print("[green]No drift detected.[/green]")
        else:
            if violations:
                console.print(
                    f"[yellow]{violations} open anchor violation(s).[/yellow]"
                )
            if pending:
                console.print(
                    f"[yellow]{pending} symbol(s) pending classification.[/yellow]"
                )
        console.print(f"[dim]Last sync: {last_sync}[/dim]")

    console.print("\n[bold cyan]2. Checking for Unassigned IDs...[/bold cyan]")
    result = await client.symbols.get_unassigned()
    unassigned = result.get("unassigned", [])
    if not unassigned:
        console.print("[green]All public symbols have assigned IDs.[/green]")
    else:
        console.print(f"[yellow]{len(unassigned)} symbol(s) with no ID tag.[/yellow]")
        for item in unassigned[:10]:
            console.print(f"   - {item.get('name')} ({item.get('file_path')})")
        if len(unassigned) > 10:
            console.print(f"   ... and {len(unassigned) - 10} more.")
        console.print(
            "\n[dim]Tip: Run 'core symbols fix-ids --write' to fix this.[/dim]"
        )
