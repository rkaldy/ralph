"""Ralph command-line application."""

import typer
from openai_codex import CodexError
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

import ui
from codex import CodexException, CodexSession
from ui import INTRO_BRIGHT

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
    GPT_MODEL_DESIGN: str | None = None
    GPT_REASONING_DESIGN: str | None = None
    GPT_MODEL_EXECUTION: str | None = None
    GPT_REASONING_EXECUTION: str | None = None

    @field_validator(
        "GPT_MODEL_DESIGN",
        "GPT_REASONING_DESIGN",
        "GPT_MODEL_EXECUTION",
        "GPT_REASONING_EXECUTION",
        mode="before",
    )
    @classmethod
    def empty_gpt_setting_as_none(cls, value: object) -> object:
        """Treat an empty INI value as an unset GPT option."""
        return None if value == "" else value


@app.callback()
def load_config(ctx: typer.Context) -> None:
    """Load Ralph configuration."""
    ctx.obj = RalphConfig()


@app.command()
def design(ctx: typer.Context, feature: str) -> None:
    config: RalphConfig = ctx.obj

    default_gpt_model, default_reasoning = CodexSession.model_settings()
    ui.intro(
        "Project Requirement Description session",
        config.GPT_MODEL_DESIGN or default_gpt_model,
        config.GPT_REASONING_DESIGN or default_reasoning,
    )

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
def execute() -> None:
    """Run the execution phase."""


def main() -> None:
    """Run the Ralph CLI."""
    app()


if __name__ == "__main__":
    main()
