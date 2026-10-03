# src/core_cli/resources/code/test.py
from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("test")
@core_command(dangerous=False)
# ID: b89ff2a7-0bf3-47cf-90ba-66a3801630c3
async def test_command() -> None:
    """Run the project test suite via pytest."""
    console.print("[bold cyan]🧪 Running test suite...[/bold cyan]")
    client = CoreApiClient()
    initial = await client.quality_tests()
    run_id = initial.get("run_id")
    if not run_id:
        console.print(f"[red]quality.tests failed to dispatch: {initial}[/red]")
        raise typer.Exit(1)
    final = await client._poll_run(run_id)
    if final.get("status") != "completed":
        console.print(f"[red]quality.tests failed: {final.get('error') or final}[/red]")
        raise typer.Exit(1)
    console.print("[green]✓ tests completed.[/green]")
