"""Ralph command-line application."""

import re
import sys
from pathlib import Path

import typer
from openai_codex import Codex, CodexError, Sandbox, SkillInput, TextInput
from pydantic_settings import BaseSettings, SettingsConfigDict


app = typer.Typer(no_args_is_help=True)
DESIGN_COMPLETE_PATTERN = re.compile(
    r"<!-- ralph:complete "
    r"path=(?P<path>tasks/prd-[a-z0-9]+(?:-[a-z0-9]+)*\.md) -->"
)


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
            return path.resolve()
    raise FileNotFoundError(f"{skill} skill is not installed")


@app.command()
def design(feature: str) -> None:
    """Interactively design a product and write its requirements to tasks/."""
    cwd = Path.cwd()

    try:
        with Codex() as codex:
            thread = codex.thread_start(
                cwd=str(cwd),
                sandbox=Sandbox.workspace_write,
            )
            result = thread.run(
                [
                    TextInput(text=f"$prd Create a PRD for this feature {feature}"),
                    SkillInput(name="prd", path=str(skill_path("prd"))),
                ]
            )

            while True:
                response = result.final_response
                if not response:
                    raise RuntimeError("Codex returned an empty response")

                completion = DESIGN_COMPLETE_PATTERN.search(response)
                visible_response = DESIGN_COMPLETE_PATTERN.sub("", response).strip()
                if visible_response:
                    typer.echo(f"\nCodex:\n{visible_response}")

                if completion:
                    relative_path = Path(completion.group("path"))
                    prd_path = (cwd / relative_path).resolve()
                    try:
                        prd_path.relative_to(cwd.resolve())
                    except ValueError as error:
                        raise RuntimeError(
                            f"Codex returned a PRD path outside the project: {relative_path}"
                        ) from error

                    if not prd_path.is_file():
                        raise RuntimeError(f"Codex did not create {relative_path}")

                    typer.echo(f"\nPRD: {relative_path}")
                    return

                answer = typer.prompt("\nYou")
                result = thread.run(answer)
    except (CodexError, FileNotFoundError, RuntimeError) as error:
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
