# src/core_cli/resources/code/bridges.py
"""CLI command: list declared architecture bridge points (issue #617)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("bridges")
@core_command(dangerous=False)
# ID: 5b2e91f3-a4c8-4d7e-b6f0-8c1a9d2e3f04
async def list_bridges_cmd(
    consuming: str | None = typer.Option(
        None,
        "--consuming",
        "-c",
        help="Filter by consuming type (e.g. AuditFinding, Proposal).",
    ),
) -> None:
    """
    List declared architecture bridge points.

    Each bridge is a constitutionally-declared data-flow crossing where
    information moves between CORE layers. Use --consuming to find bridges
    that consume a specific data type.

    Example:
      core code bridges --consuming AuditFinding
    """
    client = CoreApiClient()
    result = await client.inspect.analysis_bridges(consuming=consuming)

    if not result.get("available"):
        console.print(f"[red]✗ Bridges unavailable: {result.get('error')}[/red]")
        raise typer.Exit(1)

    bridges = result.get("bridges", [])
    if not bridges:
        if consuming:
            console.print(
                f"[yellow]No bridges found consuming type '{consuming}'.[/yellow]"
            )
        else:
            console.print("[yellow]No bridge declarations found.[/yellow]")
        return

    title = (
        f"Architecture Bridges (consuming '{consuming}')"
        if consuming
        else "Architecture Bridges"
    )
    table = Table(title=title, header_style="bold cyan", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Bridge Class", style="bold")
    table.add_column("Layer", style="blue")
    table.add_column("Source", style="dim")
    table.add_column("Sink Target", style="green")
    table.add_column("Attribution", style="magenta")
    table.add_column("ADRs", style="dim")

    for bridge in bridges:
        source = bridge.get("source_layer") or (bridge.get("source_context", "")[:40])
        attr_mechanism = bridge.get("attribution_mechanism", "")
        attr_field = bridge.get("attribution_field")
        attribution = (
            f"{attr_mechanism} → {attr_field}" if attr_field else attr_mechanism
        )
        table.add_row(
            bridge.get("id", ""),
            bridge.get("bridge_class", ""),
            bridge.get("bridge_layer", ""),
            source,
            bridge.get("sink_target", ""),
            attribution,
            ", ".join(bridge.get("authority_adrs", [])),
        )

    console.print(table)
