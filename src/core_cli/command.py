"""``core_command`` — runs an async Typer command and reports failures.

core-cli's own replacement for core-runtime's decorator of the same name. It
does only what an HTTP client needs: run the coroutine, show the dry-run
banner for dangerous commands, ask for confirmation, and turn an exception
into a clean error and exit code 1. It never builds a CORE context.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import sys
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console
from rich.markup import escape


console = Console()


def _confirm(message: str) -> bool:
    if not sys.stdin.isatty():
        console.print(
            f"{message}\n[yellow]No interactive terminal — cancelled. Run it from "
            "a terminal to confirm.[/yellow]"
        )
        return False
    return typer.confirm(message, default=False)


# ID: b7b9aa4c-a723-411e-8d37-9eb18903259e
def core_command(
    *, dangerous: bool = False, confirmation: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap an async command.

    ``dangerous`` commands that take a ``write`` flag print a dry-run banner
    when it is off; with ``confirmation`` they ask before running with it on.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        has_write = "write" in inspect.signature(func).parameters

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            write = bool(kwargs.get("write", False))
            if dangerous and has_write and not write:
                console.print(
                    "[bold yellow]⚠️  DRY RUN MODE[/bold yellow]\n"
                    "   No changes will be made. Use [cyan]--write[/cyan] to apply.\n"
                )
            if (
                dangerous
                and confirmation
                and write
                and not _confirm("🚨 Confirm this operation?")
            ):
                raise typer.Exit(0)
            try:
                return asyncio.run(func(*args, **kwargs))
            except typer.Exit:
                raise
            except Exception as exc:
                console.print(
                    "\n[bold red]❌ Command failed:[/bold red]\n   "
                    + escape(f"{type(exc).__name__}: {exc}")
                )
                raise typer.Exit(1) from exc

        return wrapper

    return decorator
