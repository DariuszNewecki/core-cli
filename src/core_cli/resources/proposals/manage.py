# src/core_cli/resources/proposals/manage.py

from __future__ import annotations

from datetime import datetime

import httpx
import typer
from rich.console import Console

from api.cli import CoreApiClient
from cli.utils import core_command


console = Console()


def _print_detailed_info(p: dict) -> None:
    console.print(f"\n[bold cyan]Proposal: {p['proposal_id']}[/bold cyan]\n")
    console.print(f"[bold]Goal:[/bold] {p.get('goal', '')}")
    console.print(f"[bold]Status:[/bold] {p['status']}")
    console.print(f"[bold]Created:[/bold] {p['created_at']}")
    console.print(f"[bold]Created By:[/bold] {p.get('created_by', '')}\n")
    risk = p.get("risk")
    if risk:
        console.print("[bold]Risk Assessment:[/bold]")
        console.print(f"  Overall: {risk['overall_risk']}")
        approval = "Yes" if p.get("approval_required") else "No"
        console.print(f"  Approval Required: {approval}")
        for factor in risk.get("risk_factors", []):
            console.print(f"    - {factor}")
        console.print("")
    actions = p.get("actions", [])
    console.print(f"[bold]Actions ({len(actions)}):[/bold]")
    for a in sorted(actions, key=lambda x: x.get("order", 0)):
        ref = a.get("action_id") or a.get("flow_id") or "?"
        console.print(f"  {a.get('order', 0) + 1}. {ref}")
        if a.get("parameters"):
            console.print(f"     Parameters: {a['parameters']}")
    scope = p.get("scope") or {}
    files = scope.get("files") or []
    modules = scope.get("modules") or []
    if files or modules:
        console.print("\n[bold]Scope:[/bold]")
        if files:
            console.print(f"  Files: {len(files)}")
        if modules:
            console.print(f"  Modules: {', '.join(modules)}")
    started = p.get("execution_started_at")
    completed = p.get("execution_completed_at")
    if started:
        console.print("\n[bold]Execution:[/bold]")
        console.print(f"  Started: {started}")
        if completed:
            dur = (
                datetime.fromisoformat(completed) - datetime.fromisoformat(started)
            ).total_seconds()
            console.print(f"  Completed: {completed}")
            console.print(f"  Duration: {dur}s")
    failure_reason = p.get("failure_reason")
    if failure_reason:
        console.print(f"\n[red]Failure Reason: {failure_reason}[/red]")


def _print_execution_summary(result: dict) -> None:
    if not result.get("ok") and "actions_executed" not in result:
        console.print(f"Error: {result.get('error', 'Unknown error')}")
        return
    console.print(f"Actions executed: {result.get('actions_executed', 0)}")
    console.print(f"Succeeded: {result.get('actions_succeeded', 0)}")
    console.print(f"Failed: {result.get('actions_failed', 0)}")
    console.print(f"Duration: {result.get('duration_sec', 0)}s\n")
    console.print("[bold]Action Results:[/bold]")
    for action_id, res in result.get("action_results", {}).items():
        mark = "[green]✓[/green]" if res["ok"] else "[red]✗[/red]"
        console.print(f"  {mark} {action_id}: {res['duration_sec']}s")
        if not res["ok"]:
            err = res.get("data", {}).get("error", "Unknown error")
            console.print(f"      [red]{err}[/red]")


@core_command(dangerous=False, requires_context=False)
# ID: 9bacc55b-be1d-4f71-a27e-6e83ba176e33
async def show_proposal(proposal_id: str = typer.Argument(...)) -> None:
    """Show detailed breakdown and risk assessment of a proposal."""
    client = CoreApiClient()
    try:
        proposal = await client.get_proposal(proposal_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            raise typer.Exit(1) from exc
        raise
    _print_detailed_info(proposal)


@core_command(dangerous=False, requires_context=False)
# ID: f2e065f7-c253-4c33-ae0d-5374ffdb8e23
async def approve_proposal(
    proposal_id: str = typer.Argument(...),
    by: str = typer.Option("cli_admin", "--by", help="Approver identity."),
    authority: str = typer.Option(
        "principal.governor",
        "--authority",
        help="Authority under which approval is granted (URS NFR.5).",
    ),
) -> None:
    """Authorize a pending proposal for execution."""
    client = CoreApiClient()
    try:
        response = await client.approve_proposal(
            proposal_id, approved_by=by, approval_authority=authority
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 404:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            raise typer.Exit(1) from exc
        if status_code == 400:
            try:
                detail = exc.response.json().get("detail", exc.response.text)
            except ValueError:
                detail = exc.response.text
            console.print(f"[red]{detail}[/red]")
            raise typer.Exit(1) from exc
        raise

    console.print(
        f"[green]✅ Proposal {proposal_id} APPROVED by "
        f"{response['approved_by']} under {response['approval_authority']}.[/green]"
    )


@core_command(dangerous=True, confirmation=True, requires_context=False)
# ID: f4cdc45a-2f42-4916-b4e3-a305b5357a9d
async def execute_proposal(
    proposal_id: str = typer.Argument(...),
    write: bool = typer.Option(False, "--write", help="Apply changes to the system."),
) -> None:
    """Execute an approved proposal.

    Runs the atomic action sequence defined in the proposal.
    """
    if not write:
        console.print("[yellow]💡 Dry-run: simulating execution steps...[/yellow]\n")
    client = CoreApiClient()
    result = await client.execute_proposal(proposal_id, write=write)
    if result.get("ok"):
        console.print(
            f"\n[bold green]✅ Execution Successful: {proposal_id}[/bold green]"
        )
    else:
        console.print(f"\n[bold red]❌ Execution Failed: {proposal_id}[/bold red]")
    _print_execution_summary(result)


@core_command(dangerous=False, requires_context=False)
# ID: 4ac3cfc1-feae-440c-b02f-4c57a6a1147d
async def reject_proposal(
    proposal_id: str = typer.Argument(...),
    reason: str = typer.Option(..., "--reason", "-r"),
) -> None:
    """Reject a proposal and prevent its execution.

    Revival of deferred findings (ADR-010 §7a / ADR-045) now happens
    on the API side; this command only renders the result.
    """
    client = CoreApiClient()
    try:
        response = await client.reject_proposal(proposal_id, reason=reason)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            raise typer.Exit(1) from exc
        raise

    console.print(f"[yellow]🚫 Proposal {response['proposal_id']} REJECTED.[/yellow]")
    revived_count = response.get("revived_count", 0)
    if revived_count > 0:
        console.print(
            f"[cyan]   Revived {revived_count} deferred "
            f"finding(s) to awaiting_reaudit for sensor adjudication.[/cyan]"
        )
