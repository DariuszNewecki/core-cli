# src/core_cli/resources/project/scout.py

"""BYOR Scout Phase B — per-rule ratification CLI over HTTP (ADR-146 D2 / ADR-119).

Calls POST /v1/project/scout to get LLM-induced + catalog-matched candidates,
then walks the operator through per-rule Accept/Downgrade/Skip ratification
(ADR-119 D5 — no --accept-all). Confirmed rules are written to:
  <path>/.intent/rules/scout_inducted.json
  <path>/.intent/enforcement/mappings/scout.yaml

File writes use direct stdlib (same as byor.py) — this is intentional; the
.intent/ tree lives in the consumer project, not in CORE, so FileHandler and
ActionExecutor (which gate CORE's own .intent/) do not apply.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.rule import Rule

from core_cli.client import CoreApiClient
from core_cli.command import core_command

from . import app


console = Console()

_ENFORCEMENT_LEVELS = ("blocking", "reporting", "advisory")
_RULES_OUTPUT = "rules/scout_inducted.json"
_MAPPINGS_OUTPUT = "enforcement/mappings/scout.yaml"


@app.command("scout")
@core_command(dangerous=True)
# ID: 55eee96e-6306-4452-a334-29c71135196e
async def scout_project(
    ctx: typer.Context,
    path: Path = typer.Argument(
        ..., help="Path to the target repository.", exists=True
    ),
    write: bool = typer.Option(
        False, "--write", help="Write inducted rules to .intent/ after ratification."
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Clear existing scout_inducted.json and re-run induction.",
    ),
) -> None:
    """Induce and ratify governance rules for a repository — Phase B (BYOR Scout).

    Calls the CORE API to extract signals and propose candidate rules
    (LLM-assisted; falls back to a universal menu when LLM is unavailable).
    Walks you through per-rule ratification. Only confirmed rules are written
    (ADR-119 D5 — no --accept-all). Requires Phase A first:
    run `project onboard <target> --write` before this command.
    """
    # path is sent as a plain string over HTTP for server-side signal
    # extraction — a relative path would resolve against the CORE API
    # process's cwd, not the caller's, and silently analyze the wrong repo.
    path = path.resolve()

    console.print(Rule("[bold cyan]Scout — Phase B: Rule Induction[/bold cyan]"))
    console.print(f"[bold cyan]Target:[/bold cyan] {path}")

    client = CoreApiClient()
    try:
        result = await client.project.scout(str(path), reset=reset)
    except Exception as exc:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError):
            detail = exc.response.json().get("detail", str(exc))
            console.print(f"[red]Scout failed: {detail}[/red]")
        else:
            console.print(f"[red]Scout failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    candidates: list[dict[str, Any]] = result.get("candidates", [])
    candidate_count = result.get("candidate_count", len(candidates))
    matched = result.get("matched", 0)

    console.print(
        f"\n[cyan]Suggest[/cyan] — {candidate_count} candidate(s) received "
        f"({matched} catalog-matched, {candidate_count - matched} declared-only)\n"
    )

    if not candidates:
        console.print(
            "[yellow]No candidate rules returned. Nothing to ratify.[/yellow]"
        )
        return

    # ── Confirm (ADR-119 D5 — mandatory per-rule ratification) ───────────────
    confirmed = _run_confirm_loop(candidates)

    if not confirmed:
        console.print("\n[yellow]No rules confirmed. Nothing written.[/yellow]")
        return

    # ── Write ─────────────────────────────────────────────────────────────────
    target_intent = path / ".intent"
    rules_json = _build_rules_document(confirmed)
    mappings_yaml = _build_mappings_document(confirmed)

    for output_rel, content in (
        (_RULES_OUTPUT, rules_json),
        (_MAPPINGS_OUTPUT, mappings_yaml),
    ):
        dest = target_intent / output_rel
        if write:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            console.print(f"[green]  ✅ Written: .intent/{output_rel}[/green]")
        else:
            console.print(f"[dim]  [DRY RUN] would write: .intent/{output_rel}[/dim]")

    enforced = sum(1 for c in confirmed if c.get("enforcement_matched"))
    declared_only = len(confirmed) - enforced

    if not write:
        console.print(
            f"\n[yellow]Dry run — {len(confirmed)} rule(s) would be written "
            f"({enforced} enforced, {declared_only} declared-only). "
            "Pass --write to apply.[/yellow]"
        )
    else:
        console.print(
            f"\n[green]✅ {len(confirmed)} rule(s) written to {target_intent} "
            f"({enforced} enforced, {declared_only} declared-only)[/green]"
        )
        console.print(
            "Next: run `core-admin code audit --offline` against this repo to enforce them."
        )


# ── Confirm loop (ADR-119 D5) ─────────────────────────────────────────────────


def _run_confirm_loop(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from rich.prompt import Prompt

    confirmed: list[dict[str, Any]] = []
    total = len(candidates)

    for idx, candidate in enumerate(candidates, start=1):
        console.print(Rule(f"Rule {idx} / {total}"))
        _display_candidate(candidate)

        try:
            choice = Prompt.ask(
                "[bold]Action[/bold]",
                choices=["a", "r", "c"],
                default="a",
                show_choices=True,
                show_default=True,
            ).lower()
        except (EOFError, KeyboardInterrupt):
            console.print(
                "\n[yellow]Confirmation interrupted — no further rules reviewed.[/yellow]"
            )
            break

        if choice == "r":
            console.print("[dim]  ↳ Rejected.[/dim]")
            continue

        if choice == "c":
            try:
                new_level = Prompt.ask(
                    "  New enforcement level",
                    choices=list(_ENFORCEMENT_LEVELS),
                    default=candidate.get("enforcement", "reporting"),
                ).lower()
            except (EOFError, KeyboardInterrupt):
                console.print(
                    "\n[yellow]Level change interrupted — rule rejected.[/yellow]"
                )
                continue
            candidate = {**candidate, "enforcement": new_level}

        console.print(f"[green]  ↳ Accepted ({candidate['enforcement']}).[/green]")
        confirmed.append(candidate)

    return confirmed


def _display_candidate(candidate: dict[str, Any]) -> None:
    rule_id = candidate.get("rule_id", "<unknown>")
    statement = candidate.get("statement", "")
    enforcement = candidate.get("enforcement", "reporting")
    rationale = candidate.get("rationale", "")
    evidence = candidate.get("evidence_sample", "")
    ramp = candidate.get("ramp_note", "")
    matched = candidate.get("enforcement_matched", False)

    color = {"blocking": "red", "reporting": "yellow", "advisory": "dim"}.get(
        enforcement, "white"
    )

    console.print("  [bold underline]OBSERVATION[/bold underline]")
    console.print(f"  [bold]ID:[/bold]          {rule_id}")
    console.print(f"  [bold]Statement:[/bold]   {statement}")
    console.print(f"  [bold]Enforcement:[/bold] [{color}]{enforcement}[/{color}]")
    console.print(f"  [bold]Rationale:[/bold]   {rationale}")
    if evidence:
        console.print(f"  [bold]Evidence:[/bold]    {evidence}")
    if ramp:
        console.print(f"  [bold]Ramp note:[/bold]   [yellow]{ramp}[/yellow]")

    console.print()
    console.print("  [bold underline]ENFORCEMENT[/bold underline]")
    if matched:
        engine = candidate.get("engine", "")
        params = candidate.get("params", {})
        scope = candidate.get("scope", {})
        applies = scope.get("applies_to", [])
        excludes = scope.get("excludes", [])
        console.print(
            f"  [bold]Engine:[/bold]      {engine} {json.dumps(params, separators=(',', ':'))}"
        )
        console.print(f"  [bold]Scope:[/bold]       applies_to {applies}")
        if excludes:
            console.print(f"               excludes   {excludes}")
    else:
        console.print(
            "  [yellow]⚠  No catalog match — rule will be declared but not enforced.[/yellow]"
        )

    console.print()
    console.print("  [dim]a = accept · r = reject · c = change enforcement level[/dim]")


# ── Output builders ────────────────────────────────────────────────────────────


def _build_rules_document(confirmed: list[dict[str, Any]]) -> str:
    rules = []
    for c in confirmed:
        rule: dict[str, Any] = {
            "id": c["rule_id"],
            "statement": c["statement"],
            "authority": "policy",
            "phase": "runtime",
            "enforcement": c["enforcement"],
            "rationale": c.get("rationale", ""),
        }
        if not c.get("enforcement_matched"):
            rule["enforcement_note"] = (
                "declared-only: no enforcement catalog entry exists for this rule."
            )
        rules.append(rule)
    doc = {
        "$schema": "META/rule_document.schema.json",
        "kind": "rule_document",
        "metadata": {
            "id": "rules.scout_inducted",
            "title": "Scout-Inducted Rules",
            "version": "1.0.0",
            "authority": "policy",
            "phase": "runtime",
            "status": "active",
        },
        "rules": rules,
    }
    return json.dumps(doc, indent=2)


def _build_mappings_document(confirmed: list[dict[str, Any]]) -> str:
    mappings: dict[str, Any] = {}
    for c in confirmed:
        if not c.get("enforcement_matched"):
            continue
        scope = c.get("scope", {})
        entry: dict[str, Any] = {
            "engine": c.get("engine", "ast_gate"),
            "params": c.get("params", {}),
            "scope": {
                "applies_to": scope.get("applies_to", ["**/*.py"]),
            },
        }
        excludes = scope.get("excludes", [])
        if excludes:
            entry["scope"]["excludes"] = excludes
        mappings[c["rule_id"]] = entry
    return yaml.dump({"mappings": mappings}, default_flow_style=False, sort_keys=False)
