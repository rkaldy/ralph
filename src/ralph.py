"""Ralph command-line application."""

import typer
from openai_codex import CodexError
from pydantic_settings import BaseSettings, SettingsConfigDict

import ui
from codex import CodexException, CodexSession

app = typer.Typer(no_args_is_help=True)


class RalphConfig(BaseSettings):
    """Configuration loaded from ``ralph.ini`` in the working directory."""

    model_config = SettingsConfigDict(
        env_file="ralph.ini",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    LINT_COMMAND: str
    TYPECHECK_COMMAND: str
    TEST_COMMAND: str


@app.callback()
def load_config(ctx: typer.Context) -> None:
    """Load Ralph configuration."""
    ctx.obj = RalphConfig()


@app.command()
def design(feature: str) -> None:
    typer.echo(ui.format_codex_response("**RALPH** Project Requirement Description session"))

    try:
        with CodexSession("prd") as session:
            with ui.codex_spinner():
                response = session.prompt(
                    f"Make an interactive user session for creating a PRD for this feature: {feature}"
                )
            while True:
                typer.echo(ui.format_codex_response(response.text))
                if response.completed:
                    typer.echo(f"\n\nPRD: {response.file}")
                    return

                answer = ui.prompt_user()
                with ui.codex_spinner():
                    response = session.prompt(answer)

    except (CodexError, CodexException) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error


@app.command()
def execute() -> None:
    """Run the execution phase."""


def main() -> None:
    """Run the Ralph CLI."""
    app()


if __name__ == "__main__":
    main()
