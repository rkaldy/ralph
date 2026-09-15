from pathlib import Path
from typing import Annotated

import typer

from config import RalphConfig
from designer import Designer
from executor import Executor

app = typer.Typer(no_args_is_help=True)


@app.callback()
def load_config(ctx: typer.Context) -> None:
    ctx.obj = RalphConfig()


@app.command()
def design(
    ctx: typer.Context,
    feature: Annotated[str, typer.Argument(help="Simple, high-level feature description")],
) -> None:
    "Run design phase and create a PRD"
    designer = Designer(ctx.obj)
    designer.design(feature)


@app.command()
def convert(
    ctx: typer.Context,
    prd: Annotated[
        Path,
        typer.Argument(
            help="Path to the Markdown PRD to convert",
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
) -> None:
    "Convert Markdown PRD to `prd.json` and split it to stories, implementable by single Codex turn"
    designer = Designer(ctx.obj)
    designer.convert(prd)


@app.command()
def execute(
    ctx: typer.Context,
) -> None:
    "Implement the feature using `prd.json`"
    executor = Executor(ctx.obj)
    executor.run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
