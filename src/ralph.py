from pathlib import Path
from typing import Annotated

import typer

from config import RalphConfig
from converter import Converter
from designer import Designer
from implementor import Implementor

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
    designer = Designer(ctx.obj, feature)
    designer.run()


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
    converter = Converter(ctx.obj, prd)
    converter.run()


@app.command()
def implement(
    ctx: typer.Context,
) -> None:
    "Implement the feature using `prd.json`"
    implementor = Implementor(ctx.obj)
    implementor.run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
