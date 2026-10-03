# src/core_cli/resources/vectors/query.py

"""Semantic vector search command — consumer CLI over HTTP (ADR-146 D2)."""

from __future__ import annotations

import typer
from rich.console import Console

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from .hub import app


console = Console()


@app.command("query")
@core_command()
# ID: 44056798-de41-4934-8bba-97e6f88ce1f0
async def query_vectors(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Natural language query"),
    collection: str = typer.Option(
        "policies",
        "--collection",
        "-c",
        help="Collection to query: 'policies', 'patterns', 'specs', or 'code'",
    ),
    limit: int = typer.Option(5, "--limit", "-n", help="Max results to return"),
) -> None:
    """Semantic search in vector collections.

    Search constitutional documents using natural language queries.

    Examples:
        core vectors query "file access rules"
        core vectors query "atomic actions" --collection patterns --limit 3
    """
    console.print(f"[bold cyan]Querying {collection}[/bold cyan]")
    console.print(f"Query: {query}")
    console.print()
    client = CoreApiClient()
    try:
        result = await client.vectors.query(query, collection=collection, limit=limit)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    results = result.get("results", [])
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    console.print(f"[bold]Top {len(results)} results:[/bold]")
    console.print("")
    for i, hit in enumerate(results, 1):
        score = hit.get("score", 0.0)
        payload = hit.get("payload") or {}
        content = payload.get("content") or payload.get("text") or ""
        doc_id = payload.get("doc_id") or payload.get("chunk_id") or "Unknown"
        content_preview = content[:200] if content else "[No content available]"
        console.print(f"[bold cyan]{i}. {doc_id}[/bold cyan] (score: {score:.4f})")
        console.print(f"   {content_preview}...")
        console.print("")
