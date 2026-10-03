# src/core_cli/resources/code/docstrings.py
from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("docstrings")
@core_command(dangerous=True)
# ID: 9f0d0239-d29d-4dff-8c32-3fdecaa809e9
async def fix_docstrings_command(
    write: bool = typer.Option(False, "--write", help="Apply changes."),
    limit: int = typer.Option(3, "--limit", help="Symbols to process."),
    file: str | None = typer.Option(
        None, "--file", help="Target a single file (repo-relative)."
    ),
) -> None:
    """Autonomously generate and inject missing docstrings using AI."""
    client = CoreApiClient()
    initial = await client.run_fix(
        "fix.docstrings",
        target_files=[file] if file else None,
        write=write,
        params={"limit": limit},
    )
    run_id = initial.get("run_id")
    if not run_id:
        console.print(f"[red]fix.docstrings failed to dispatch: {initial}[/red]")
        raise typer.Exit(1)
    final = await client._poll_run(run_id)
    if final.get("status") != "completed":
        console.print(
            f"[red]fix.docstrings failed: {final.get('error') or final}[/red]"
        )
        raise typer.Exit(1)
    console.print("[green]✓ fix.docstrings completed.[/green]")
