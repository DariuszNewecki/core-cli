# core-cli

The consumer command-line tool for [CORE](https://github.com/DariuszNewecki/CORE): review
and approve proposals, run checks and fixes on the repository CORE governs, onboard a
repository (BYOR), and work the assisted remediation lane. Its binary is called `core`.

`core-cli` is an HTTP client and nothing more. Every command talks to a **running CORE
API**, using only the routes in CORE's published
[OpenAPI contract](https://github.com/DariuszNewecki/CORE/blob/main/docs/reference/openapi.json);
it does not install or import CORE. The operator tool, `core-admin`, ships separately in
`core-runtime` and covers the CORE installation itself: secrets, vector store, database
sync ([which one do I need?](https://dariusznewecki.github.io/CORE/cli-reference/)).

## Prerequisites

- Python 3.12+
- A reachable CORE API, which itself needs PostgreSQL and Qdrant. See CORE's
  [getting started](https://dariusznewecki.github.io/CORE/getting-started/).

> **No authentication.** OSS CORE runs in trusted-localhost mode: the API binds to
> loopback and accepts every request. Anyone who can reach it can approve and execute
> proposals. Keep it on `127.0.0.1` and do not expose it on a shared network.

## Install

```bash
pip install core-cli
```

Its only dependencies are `typer`, `rich`, `httpx` and `PyYAML`.

## Configure

`core` uses `http://127.0.0.1:8000` unless you point it elsewhere:

```bash
export CORE_API_URL=http://127.0.0.1:8000
```

## Use

```bash
core proposals list                 # proposals awaiting a decision
core proposals show <id>            # risk assessment and planned changes
core lane list                      # delegated findings waiting for assisted remediation
core project onboard <path>         # preview delivering the machinery floor (BYOR)
core project onboard <path> --write # deliver it
core <group> <command> --help       # options for any command
```

Commands that change files or data **preview by default** and act only with `--write`.

## Commands

| Group | What it covers |
|---|---|
| `proposals` | `list`, `show`, `create`, `approve`, `reject`, `execute`, `integrate` |
| `lane` | `list`, `next`, `claim`, `propose`: assisted remediation of delegated findings |
| `project` | `onboard`, `scout`, `promote`, `docs`: bring a repository under governance (BYOR) |
| `code` | quality and verification: `lint`, `format`, `test`, `check-imports`, `audit-duplicates`, … |
| `symbols` | `audit`, `fix-ids`, `resolve-duplicates` |
| `vectors` | `query`: semantic search over the governed repository |

Every command, option and default is in the generated
[`core` command reference](https://dariusznewecki.github.io/CORE/reference/core/).

## Architecture

The split between the consumer CLI (`core`) and the operator CLI (`core-admin`) is
recorded in
[ADR-146](https://github.com/DariuszNewecki/CORE/blob/main/.specs/decisions/ADR-146-cli-consumer-operator-split.md):
`core` covers operations on the repository CORE governs; `core-admin` covers the CORE
installation. `tests/test_contract.py` checks every route this client calls against CORE's
OpenAPI contract.

## License

MIT. See [LICENSE](LICENSE).
