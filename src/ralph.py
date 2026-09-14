"""Ralph command-line application."""

import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Thread

import typer
from openai_codex import Codex, CodexError, Sandbox, SkillInput, TextInput
from pydantic_settings import BaseSettings, SettingsConfigDict


app = typer.Typer(no_args_is_help=True)
CODEX_COLOR = (224, 255, 224)
USER_COLOR = (255, 224, 128)
BOLD_COLOR = (255, 255, 255)
SPINNER_FRAMES = ("⢹", "⣸", "⣴", "⣦", "⣇", "⡏", "⠟", "⠻")
SPINNER_INTERVAL = 0.08
SPINNER_LABEL = ""
CODEX_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
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


def prompt_user() -> str:
    """Read a response while keeping the prompt and terminal input orange."""
    typer.echo()
    typer.secho("╭─", fg=USER_COLOR)
    typer.echo(typer.style("╰─❯ ", fg=USER_COLOR, reset=False), nl=False)
    try:
        return input()
    finally:
        typer.echo(typer.style("", reset=True), nl=False)


def format_codex_response(response: str) -> str:
    """Render Markdown-style bold spans for terminal output."""
    rendered: list[str] = []
    position = 0

    for match in CODEX_BOLD_PATTERN.finditer(response):
        rendered.append(typer.style(response[position : match.start()], fg=CODEX_COLOR))
        rendered.append(typer.style(match.group(1), fg=BOLD_COLOR))
        position = match.end()

    rendered.append(typer.style(response[position:], fg=CODEX_COLOR))
    return "".join(rendered)


@contextmanager
def codex_spinner() -> Iterator[None]:
    """Display an animated Braille spinner while waiting for Codex."""
    if not sys.stdout.isatty():
        yield
        return

    stopped = Event()

    def animate() -> None:
        frame_index = 0
        while not stopped.is_set():
            frame = SPINNER_FRAMES[frame_index % len(SPINNER_FRAMES)]
            message = typer.style(f"{frame} {SPINNER_LABEL}", fg=CODEX_COLOR)
            typer.echo(f"\r{message}", nl=False)
            frame_index += 1
            stopped.wait(SPINNER_INTERVAL)

    typer.echo()
    worker = Thread(target=animate, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stopped.set()
        worker.join()
        typer.echo(f"\r{' ' * (len(SPINNER_LABEL) + 2)}\r", nl=False)


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
            with codex_spinner():
                result = thread.run(
                    [
                        TextInput(
                            text=(
                                "Make an interactive user session for "
                                f"creating a PRD for this feature: {feature}"
                            )
                        ),
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
                    typer.echo(format_codex_response(visible_response))

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

                answer = prompt_user()
                with codex_spinner():
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
