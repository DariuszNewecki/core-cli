# src/core_cli/resources/project/onboard.py

"""BYOR onboarding commands — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command

from . import app


console = Console()


@app.command("onboard")
@core_command(dangerous=True, requires_context=False, requires_brain_services=False)
# ID: e625b650-05c8-421e-9cf7-073917b43dc9
async def onboard_project(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="Path to existing repository."),
    write: bool = typer.Option(
        False, "--write", help="Write .intent/ directory to the target path."
    ),
    stage: bool = typer.Option(
        False,
        "--stage",
        help=(
            "Write to work/staged/<name>/ for inspection before promoting "
            "(ADR-123). Requires --write; ignored in dry-run mode."
        ),
    ),
) -> None:
    """Onboard an existing repository into CORE governance — Phase A (BYOR).

    Delivers the machinery floor (META schemas, taxonomies, constitution stub,
    enforcement/config) into the target's .intent/. No rules are included; run
    `project scout` afterwards to induce and ratify rules for this repo (ADR-119).
    Dry-run by default; pass --write to apply.

    Pass --write --stage to write to work/staged/<name>/ first, inspect the
    files, then run `project onboard promote <path>` to deliver to the target.
    """
    if stage and not write:
        console.print(
            "[yellow]--stage has no effect without --write "
            "(dry-run already previews the delivery).[/yellow]"
        )

    if stage and write:
        mode_label = "Staging onboard for (→ staged/<name>)"
    elif write:
        mode_label = "Onboarding"
    else:
        mode_label = "Previewing onboarding for"

    console.print(
        f"[bold cyan]{mode_label} repository (Phase A — machinery floor):[/bold cyan] {path}"
    )

    client = CoreApiClient()
    try:
        result = await client.project.onboard(str(path), write=write, stage=stage)
    except Exception as exc:
        console.print(f"[red]Onboard failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    mode = result.get("mode", "dry-run")
    stage_dir = result.get("stage_dir")

    if stage_dir:
        console.print(
            f"\n[bold green]Staged to[/bold green] {stage_dir}/.intent\n"
            f"[dim]Inspect, then run:[/dim]  "
            f"[bold]core-admin project onboard promote {path}[/bold]"
        )
    elif mode == "dry-run":
        console.print("[yellow]DRY-RUN complete. Pass --write to apply.[/yellow]")
    else:
        console.print(f"[green]Onboarding complete ({mode}).[/green]")


@app.command("promote")
@core_command(dangerous=True, requires_context=False, requires_brain_services=False)
# ID: d2eafb4d-7ead-4d04-bb89-8d78eda8a582
async def promote_onboard(
    ctx: typer.Context,
    path: Path = typer.Argument(
        ...,
        help="Target repository path (same path used with --stage).",
    ),
) -> None:
    """Promote a staged machinery floor into the target repository (ADR-123).

    Reads from work/staged/<name>/.intent/ (within CORE's repo) and writes to
    <path>/.intent/. Run `project onboard promote --help` for full lifecycle details.
    """
    console.print(f"[bold cyan]Promoting staged onboard to:[/bold cyan] {path}")
    client = CoreApiClient()
    try:
        await client.project.promote(str(path))
    except Exception as exc:
        console.print(f"[red]Promote failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[bold green]Promoted to[/bold green] {Path(path).resolve() / '.intent'}")
