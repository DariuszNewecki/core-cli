# src/cli/resources/vectors/hub.py
import typer


app = typer.Typer(
    name="vectors",
    help="Semantic search over the governed repository's vector index.",
    no_args_is_help=True,
)
