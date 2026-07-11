# src/core_cli/resources/secrets/manage.py

"""Encrypted secrets management — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from api.cli import CoreApiClient
from cli.utils import core_command

from .hub import app


console = Console()


@app.command("set")
@core_command(dangerous=True, requires_context=False)
# ID: 92bcc7e9-189f-45d0-bc18-21512bcba69f
async def set_secret(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Secret key (e.g., 'anthropic.api_key')"),
    value: str = typer.Option(
        ...,
        "--value",
        "-v",
        prompt=True,
        hide_input=True,
        help="Secret value (will be encrypted at rest)",
    ),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Optional description"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite without 409 error if key exists"
    ),
) -> None:
    """Store an encrypted secret in the CORE installation."""
    if not key.strip():
        console.print("[red]Secret key cannot be empty.[/red]")
        raise typer.Exit(code=1)
    client = CoreApiClient()
    try:
        result = await client.secrets.set_secret(
            key=key, value=value, description=description, force=force
        )
    except Exception as exc:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 409:
            console.print(
                f"[red]Secret '{key}' already exists. Use --force to overwrite.[/red]"
            )
            raise typer.Exit(code=1) from exc
        console.print(f"[red]Failed to store secret: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    action = result.get("action", "stored")
    console.print(f"[green]Secret '{key}' {action}.[/green]")


@app.command("get")
@core_command(dangerous=False, requires_context=False)
# ID: 01608ce2-3fb8-4f0d-ae1a-abaec72369d7
async def get(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Secret key to retrieve"),
    show: bool = typer.Option(False, "--show", "-s", help="Display the secret value"),
) -> None:
    """Check whether a secret exists (optionally reveal value with --show)."""
    client = CoreApiClient()
    try:
        result = await client.secrets.get_secret(key=key, show=show)
    except Exception as exc:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
            console.print(f"[red]Secret '{key}' not found.[/red]")
            raise typer.Exit(code=1) from exc
        raise
    if show:
        console.print(f"[bold]Secret '{key}':[/bold]")
        console.print(result.get("value", ""))
    else:
        console.print(f"[green]Secret '{key}' exists.[/green]")


@app.command("list")
@core_command(dangerous=False, requires_context=False)
# ID: cf23ee88-7f5e-47e9-91de-7414ef0c36ed
async def list_secrets(ctx: typer.Context) -> None:
    """List all secret keys in the CORE installation (values not shown)."""
    client = CoreApiClient()
    result = await client.secrets.list_secrets()
    secrets = result.get("secrets") or []
    if not secrets:
        console.print("[yellow]No secrets found.[/yellow]")
        return
    table = Table(title="Encrypted Secrets")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Last Rotated", style="dim")
    table.add_column("Created", style="dim")
    for s in secrets:
        table.add_row(
            s["key"],
            str(s.get("last_rotated_at") or "never"),
            str(s.get("created_at") or "unknown"),
        )
    console.print(table)
    console.print(f"[dim]Total: {result.get('count', len(secrets))} secrets[/dim]")


@app.command("delete")
@core_command(dangerous=True, requires_context=False)
# ID: cc76acdd-0ef9-4602-86b0-09580546dd05
async def delete(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Secret key to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Permanently delete a secret from the CORE installation."""
    if not yes:
        typer.confirm(f"Delete secret '{key}'?", abort=True)
    client = CoreApiClient()
    try:
        await client.secrets.delete_secret(key)
    except Exception as exc:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
            console.print(f"[red]Secret '{key}' not found.[/red]")
            raise typer.Exit(code=1) from exc
        raise
    console.print(f"[green]Secret '{key}' deleted.[/green]")


@app.command("rotate")
@core_command(dangerous=True, requires_context=False)
# ID: 634e4701-120b-4a5e-88ef-f4cb0db315a9
async def rotate(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Secret key to rotate"),
    new_value: str = typer.Option(
        ..., "--value", "-v", prompt=True, hide_input=True, help="New secret value"
    ),
) -> None:
    """Rotate the value of an existing secret (updates last_rotated_at)."""
    client = CoreApiClient()
    try:
        await client.secrets.rotate_secret(key, new_value)
    except Exception as exc:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
            console.print(f"[red]Secret '{key}' not found.[/red]")
            raise typer.Exit(code=1) from exc
        raise
    console.print(f"[green]Secret '{key}' rotated.[/green]")
