# core-cli

Consumer governance CLI for [CORE](https://github.com/DariuszNewecki/CORE) — pure HTTP client for governing repositories against CORE constitutional rules.

## Install

```bash
pip install core-cli
```

## Usage

```bash
core lane list
core proposals list
core code audit_duplicates --help
core symbols audit --help
core vectors query --help
core project onboard --help
```

Requires a running CORE instance. Configure via environment:

```bash
export CORE_API_URL=http://localhost:8000
```

## Commands

| Namespace | Commands |
|-----------|----------|
| `lane` | `list`, `next`, `claim`, `propose` |
| `proposals` | `list`, `create`, `show`, `approve`, `reject`, `execute` |
| `secrets` | manage encrypted secrets |
| `code` | `actions`, `audit_duplicates`, `bridges`, `check_imports`, `check_ui`, `docstrings`, `fix_atomic`, `format`, `integrity`, `lint`, `logging`, `test` |
| `symbols` | `audit`, `fix_ids`, `resolve_duplicates`, `sync` |
| `vectors` | `query`, `rebuild`, `status`, `sync`, `sync_code` |
| `project` | `docs`, `onboard`, `promote`, `scout` |

## Architecture

All commands communicate exclusively over the CORE HTTP API — no in-process access required.
`core-cli` depends on `core-runtime` for shared HTTP client infrastructure (`api.cli.*`)
and CLI utilities (`cli.utils.*`).

See [ADR-146](https://github.com/DariuszNewecki/CORE/blob/main/.specs/decisions/ADR-146-cli-consumer-operator-split.md) for the consumer/operator split rationale.
