# src/core_cli/resources/vectors/rebuild.py

"""Rebuild a Qdrant collection — consumer CLI over HTTP (ADR-146 D2).

A real rebuild is three coordinated operations (per #203):
  1. Delete the Qdrant collection.
  2. Reset core.repo_artifacts.chunk_count = 0 for targeted rows.
  3. RepoEmbedderWorker repopulates organically on its next cycle.

The CORE API route handles all three; this file is the thin CLI surface.
"""

from __future__ import annotations

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("rebuild")
@core_command(dangerous=True, requires_context=False)
# ID: f0398939-3c90-4972-b8bf-1241dcc6b732
async def rebuild_collection(
    ctx: typer.Context,
    collection: str = typer.Option(
        ...,
        "--collection",
        "-c",
        help="Qdrant collection to rebuild (e.g. core-code, core-specs).",
    ),
    write: bool = typer.Option(
        False, "--write", help="Apply the rebuild (default: dry-run)."
    ),
) -> None:
    """Delete a Qdrant collection and reset chunk_count so it repopulates.

    Dry-run by default — shows how many artifacts would be re-embedded.
    Pass --write to delete the collection and reset chunk_count.
    """
    client = CoreApiClient()
    try:
        result = await client.vectors.rebuild(collection, write=write)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    if not write:
        total = result.get("artifacts_total", 0)
        reset = result.get("artifacts_to_reset", 0)
        console.print(f"[bold cyan]Vector rebuild — {collection}[/bold cyan]")
        console.print(f"Artifacts targeting collection: {total} (embedded: {reset})")
        console.print(
            f"[yellow]DRY-RUN:[/yellow] would delete '{collection}' and reset "
            f"chunk_count=0 on {reset} artifact(s). Use --write to apply."
        )
    else:
        reset = result.get("artifacts_reset", 0)
        console.print(f"[green]Deleted[/green] Qdrant collection '{collection}'.")
        console.print(
            f"[green]Reset[/green] chunk_count=0 on {reset} artifact(s)."
        )
        console.print(
            "[dim]RepoEmbedderWorker will recreate the collection on its next cycle.[/dim]"
        )
