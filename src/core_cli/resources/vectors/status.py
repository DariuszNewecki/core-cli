# src/core_cli/resources/vectors/status.py

"""Vector store status command — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("status")
@core_command(dangerous=False, requires_context=False)
# ID: 61334967-75a9-4a0a-96aa-00e53698b7e8
async def status_vectors(ctx: typer.Context) -> None:
    """Show vector store health and collection statistics."""
    client = CoreApiClient()
    try:
        result = await client.vectors.status()
    except Exception as exc:
        console.print(f"[bold red]Qdrant Connection Failed:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    collections = result.get("collections", [])
    if not collections:
        console.print("[yellow]No Qdrant collections found.[/yellow]")
        return
    table = Table(title="Qdrant Collections")
    table.add_column("Collection", style="cyan")
    table.add_column("Status", justify="center")
    for coll in collections:
        table.add_row(coll["name"], coll.get("status", "active"))
    console.print(table)
