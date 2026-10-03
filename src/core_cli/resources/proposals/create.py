# src/core_cli/resources/proposals/create.py

from __future__ import annotations

import httpx
import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command


console = Console()


def _parse_action_options(action_strs: list[str]) -> list[dict]:
    """Parse CLI action strings (action_id:key=val) into plain dicts.

    Returns dicts with keys {action_id, parameters, order} matching the
    POST /v1/proposals action body schema. Preserves input order.
    """
    proposal_actions: list[dict] = []
    for i, action_str in enumerate(action_strs):
        if ":" in action_str:
            action_id, params_str = action_str.split(":", 1)
            parameters: dict[str, str] = {}
            for param in params_str.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    parameters[key.strip()] = value.strip()
        else:
            action_id = action_str
            parameters = {}
        proposal_actions.append(
            {"action_id": action_id, "parameters": parameters, "order": i}
        )
    return proposal_actions


@core_command(dangerous=True)
# ID: e3cc0065-b821-49dd-b90e-df86633d01c6
async def create_proposal(
    goal: str = typer.Argument(..., help="Strategic goal of the proposal."),
    actions: list[str] = typer.Option(
        [], "--action", "-a", help="Format: action_id:param=value"
    ),
    files: list[str] = typer.Option(
        [], "--file", "-f", help="Specific files affected."
    ),
    write: bool = typer.Option(
        False, "--write", help="Persist the proposal. Dry-run by default."
    ),
) -> None:
    """Create a new autonomous proposal for system modification.

    Validates the plan and performs an initial risk assessment.
    """
    console.print(f"[bold cyan]📝 Crafting Proposal:[/bold cyan] {goal}")
    proposal_actions = _parse_action_options(actions)
    if not proposal_actions:
        console.print(
            "[yellow]⚠️ Warning: No actions specified. "
            "Proposal created as placeholder.[/yellow]"
        )

    client = CoreApiClient()
    try:
        response = await client.create_proposal(
            goal=goal,
            actions=proposal_actions,
            files=files,
            write=write,
        )
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        console.print(f"[red]Proposal creation failed: {detail}[/red]")
        raise typer.Exit(1) from exc

    proposal = response["proposal"]
    risk_level = proposal["risk"]["overall_risk"] if proposal.get("risk") else "unknown"
    console.print(f"Risk Tier: [bold]{risk_level.upper()}[/bold]")

    if not write:
        console.print(
            "[yellow]⚠️  DRY RUN MODE — No changes made. "
            "Use --write to persist.[/yellow]"
        )
        console.print(f"[dim]Proposal goal: {proposal['goal']}[/dim]")
        return

    console.print(
        f"[green]✅ Proposal created: [bold]{proposal['proposal_id']}[/bold][/green]"
    )
    console.print(
        f"[dim]Run 'core proposals approve {proposal['proposal_id']}' to authorize.[/dim]"
    )
