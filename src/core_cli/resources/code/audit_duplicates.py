# src/core_cli/resources/code/audit_duplicates.py
from __future__ import annotations

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("audit-duplicates")
@core_command(dangerous=False, requires_context=False)
# ID: 2ad098e5-aa8a-4e12-89e4-be20d2e12e03
async def audit_duplicates_cmd(
    threshold: float = typer.Option(0.96, help="Similarity threshold (0.0-1.0)."),
) -> None:
    """
    Perform a semantic scan to find duplicate logic across the codebase.
    Helps enforce the 'dry_by_design' constitutional principle.
    """
    client = CoreApiClient()
    result = await client.inspect.analysis_duplicates(threshold=threshold)
    if result.get("ok"):
        console.print(
            f"[green]✓ Duplicates scan complete (threshold={threshold}).[/green]"
        )
        note = result.get("note", "")
        if note:
            console.print(f"[dim]{note}[/dim]")
    else:
        console.print(f"[red]✗ Duplicates scan failed: {result.get('error')}[/red]")
        raise typer.Exit(1)
