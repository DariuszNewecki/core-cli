# src/core_cli/resources/proposals/integrate.py
"""`core proposals integrate` — commit the governed repository's staged work.

Calls POST /v1/integrate: CORE stages, formats/lints and commits the working
tree of the repository it governs.
"""

from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command


console = Console()


@core_command(dangerous=True)
# ID: f779e122-cafa-44a9-80cc-b4b1a31cc363
async def integrate_cmd(
    commit_message: str = typer.Option(
        ..., "-m", "--message", help="The git commit message for this integration."
    ),
    write: bool = typer.Option(
        False, "--write", help="Commit and integrate staged changes (default: dry-run)."
    ),
) -> None:
    """Integrate staged changes into the governed repository and commit them."""
    if not write:
        return
    console.print("[bold cyan]🚀 Integrating staged changes...[/bold cyan]")
    await CoreApiClient().integrate(commit_message=commit_message)
    console.print(
        "[bold green]✅ Changes successfully integrated and committed.[/bold green]"
    )
