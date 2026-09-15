import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Thread

import typer

from stream import CODEX_OUTPUT_COLOR

INTRO_BRIGHT = (255, 240, 224)
INTRO_DARK = (128, 120, 112)
USER_BACKGROUND = (32, 32, 32)
USER_FOREGROUND = typer.colors.BRIGHT_WHITE
SPINNER_FRAMES = ("⢹", "⣸", "⣴", "⣦", "⣇", "⡏", "⠟", "⠻")
SPINNER_INTERVAL = 0.08
SPINNER_LABEL = ""


def intro(mode: str) -> None:
    """Print the -framed heading for a design session."""
    title = f"Ralph {mode}"
    directory = f"directory: {Path.cwd()}"
    content_width = max(len(f"Ralph {mode}"), len(directory)) + 10

    def border(text: str) -> str:
        return typer.style(text, fg=INTRO_DARK)

    typer.echo(border(f"╭{'─' * (content_width + 2)}╮"))
    typer.echo(
        border("│ ")
        + typer.style("Ralph ", fg=INTRO_BRIGHT, bold=True)
        + typer.style(mode, fg=INTRO_BRIGHT)
        + typer.style(" " * (content_width - len(title)))
        + border(" │")
    )
    typer.echo(border(f"│{' ' * (content_width + 2)}│"))
    typer.echo(
        border("│ ")
        + typer.style("directory: ", fg=INTRO_DARK)
        + typer.style(Path.cwd(), fg=INTRO_BRIGHT)
        + typer.style(" " * (content_width - len(directory)))
        + border(" │")
    )
    typer.echo(border(f"╰{'─' * (content_width + 2)}╯"))


def prompt_user() -> str:
    """Read a response in a Codex CLI-style input block."""
    terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    row = typer.style(
        " " * max(terminal_width - 1, 1),
        bg=USER_BACKGROUND,
    )

    for _ in range(3):
        typer.echo(row)
    typer.echo("\033[2A\r", nl=False)
    typer.echo(
        typer.style(
            "› ",
            fg=USER_FOREGROUND,
            bg=USER_BACKGROUND,
            reset=False,
        ),
        nl=False,
    )
    try:
        return input()
    finally:
        typer.echo(typer.style("", reset=True), nl=False)
        typer.echo()


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
            message = typer.style(f"{frame} {SPINNER_LABEL}", fg=CODEX_OUTPUT_COLOR)
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
