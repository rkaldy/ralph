from pathlib import Path
from typing import Annotated

import typer

from ralph.config import RalphConfig
from ralph.runners.converter import Converter
from ralph.runners.designer import Designer
from ralph.runners.programmer import Programmer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def load_config(ctx: typer.Context) -> None:
    ctx.obj = RalphConfig()


@app.command()
def designer(
    ctx: typer.Context,
    feature: Annotated[
        str | None,
        typer.Argument(help="Simple, high-level feature description"),
    ] = None,
    feature_file: Annotated[
        Path | None,
        typer.Option(
            "--file",
            "-f",
            help="Read the feature description from a text file",
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    "Run design phase and create a PRD"
    if feature_file is not None:
        feature = feature_file.read_text(encoding="utf-8")
    if feature is None:
        raise typer.BadParameter("Provide FEATURE or -f")
    if not (feature := feature.strip()):
        raise typer.BadParameter("Feature description must not be empty")

    designer = Designer(ctx.obj, feature)
    designer.run()


@app.command()
def converter(
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
def programmer(
    ctx: typer.Context,
) -> None:
    "Code the feature using `prd.json`"
    programmer = Programmer(ctx.obj)
    programmer.run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
