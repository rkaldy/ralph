import re
import sys
from contextlib import contextmanager
from threading import Event, Thread
from typing import Iterator

import typer

CODEX_COLOR = (224, 255, 224)
USER_COLOR = (255, 224, 128)
BOLD_COLOR = (255, 255, 255)
SPINNER_FRAMES = ("⢹", "⣸", "⣴", "⣦", "⣇", "⡏", "⠟", "⠻")
SPINNER_INTERVAL = 0.08
SPINNER_LABEL = ""
CODEX_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


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
        rendered.append(typer.style(match.group(1), fg=BOLD_COLOR, bold=True))
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

