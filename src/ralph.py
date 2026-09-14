"""Ralph command-line application."""

import subprocess
import sys
from pathlib import Path

import typer
from pydantic_settings import BaseSettings, SettingsConfigDict


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


def skill_path(skill: str) -> Path:
    checkout_skill = Path(__file__).resolve().parent.parent / f"skills/{skill}/SKILL.md"
    installed_skill = (
        Path(sys.prefix) / f"share/ralph/skills/{skill}/SKILL.md"
    )

    for path in (checkout_skill, installed_skill):
        if path.is_file():
            return path
    raise FileNotFoundError(f"{skill} skill is not installed")


@app.command()
def design() -> None:
    try:
        path = skill_path("design")
        result = subprocess.run(
            [
                "codex",
                "--cd",
                str(Path.cwd()),
                "--sandbox",
                "workspace-write",
                "--ask-for-approval",
                "on-request",
                (
                    f"$design Create a PRD of an user-,"
                ),
            ],
            check=False,
        )
    except FileNotFoundError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=127) from error

    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command()
def execute() -> None:
    """Run the execution phase."""


def main() -> None:
    """Run the Ralph CLI."""
    app()


if __name__ == "__main__":
    main()
