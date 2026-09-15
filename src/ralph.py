"""Ralph command-line application."""

from pathlib import Path
from typing import Annotated

import typer
from openai_codex import CodexError

import ui
from codex import CodexException, CodexSession
from config import RalphConfig
from ui import INTRO_BRIGHT

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
    config: RalphConfig = ctx.obj
    ui.intro("Project Requirement Description session", config.GPT_MODEL_DESIGN, config.GPT_REASONING_DESIGN)

    try:
        with CodexSession(
            "prd",
            model=config.GPT_MODEL_DESIGN,
            reasoning=config.GPT_REASONING_DESIGN,
        ) as session:
            response = session.prompt(
                f"Make an interactive user session for creating a PRD for this feature: {feature}"
            )
            while True:
                if response.completed:
                    typer.echo(
                        typer.style("Design session completed. The generated PRD is at ", fg=INTRO_BRIGHT)
                        + typer.style(response.file, fg=INTRO_BRIGHT, bold=True)
                        + typer.style(" .\nReview and update it and then run ", fg=INTRO_BRIGHT)
                        + typer.style(f"ralph execute {response.file}", fg=INTRO_BRIGHT, bold=True)
                        + typer.style(" .\n", fg=INTRO_BRIGHT)
                    )
                    return

                answer = ui.prompt_user()
                response = session.prompt(answer)

    except (CodexError, CodexException) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error


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
    config: RalphConfig = ctx.obj
    ui.intro(
        "PRD conversion",
        config.GPT_MODEL_DESIGN,
        config.GPT_REASONING_DESIGN,
    )

    output_path = Path.cwd() / "prd.json"
    try:
        with CodexSession(
            "convert",
            model=config.GPT_MODEL_DESIGN,
            reasoning=config.GPT_REASONING_DESIGN,
        ) as session:
            response = session.prompt(f"Convert the Markdown PRD at {prd} to {output_path}.")

        if not response.file or response.file.resolve() != output_path.resolve():
            raise CodexException("Codex did not complete the conversion to prd.json")

        typer.echo(
            typer.style("Conversion completed. The generated JSON PRD is at ", fg=INTRO_BRIGHT)
            + typer.style(output_path, fg=INTRO_BRIGHT, bold=True)
            + typer.style(" .\n", fg=INTRO_BRIGHT)
        )
    except (CodexError, CodexException) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error


@app.command()
def execute(
    ctx: typer.Context,
) -> None:
    "Implement the feature using `prd.json`"
    config: RalphConfig = ctx.obj
    ui.intro("Agentic coding", config.GPT_MODEL_EXECUTION, config.GPT_REASONING_EXECUTION)

    try:
        with CodexSession(
            "execute",
            model=config.GPT_MODEL_EXECUTION,
            reasoning=config.GPT_REASONING_EXECUTION,
        ) as session:
            pass

    except (CodexError, CodexException) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error


def main() -> None:
    app()


if __name__ == "__main__":
    main()
