import typer
from rich.console import Console
from rich.control import Control
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text
from rich.theme import Theme

from exceptions import RalphError

theme = Theme(
    {
        "meta": "#ffe8c8",
        "metabold": "bold #ffe8c8",
        "metadark": "#807870",
        "command": "#e0ffe0",
        "spinner": "#a08060",
        "user": "#ffffff on #202020",
        "reasoning": "#808080",
    }
)

console = Console(theme=theme)


class LinePreservingMarkdown(Markdown):
    def __init__(self, markup: str, style: str) -> None:
        super().__init__(markup, style=style)
        for token in self._flatten_tokens(self.parsed):
            if token.type == "softbreak":
                token.type = "hardbreak"


class LiveRow:
    def __init__(self, initial_buffering: int = 0) -> None:
        self.style = "none"
        self.live = Live(
            Spinner(name="dots2", text=Text("Thinking", style="metadark"), style="metadark"),
            console=console,
            refresh_per_second=15,
        )
        self.buffer = ""
        self.initial_buffering = initial_buffering
        self.live.start()

    def text(self, text: Text) -> None:
        self.live.update(text)
        self.live.stop()

    def start(self, delta: str, style: str | None = None) -> None:
        if style:
            self.style = style
        self.update(delta)

    def update(self, delta: str) -> None:
        self.buffer += delta
        if len(self.buffer) > self.initial_buffering:
            self.live.update(LinePreservingMarkdown(self.buffer, style=self.style))

    def stop(self) -> None:
        self.live.stop()

    def match(self, pattern: str) -> bool:
        return pattern in self.buffer

    def clear(self) -> None:
        self.buffer = ""


def prompt_user() -> str:
    row = Text(" " * max(console.width - 1, 1), style="user")

    console.print()
    for _ in range(3):
        console.print(row, highlight=False)
    console.control(Control.move(0, -2))
    try:
        console.print("› ", end="", style="user")
        console.file.write(typer.style("", fg="bright_white", bg=(32, 32, 32), reset=False))
        console.file.flush()
        return console.input()
    except EOFError as ex:
        raise RalphError("Interrupted") from ex
    finally:
        console.file.write(typer.style("", reset=True))
        console.print()
        console.print()


def horizontal_line() -> None:
    console.print()
    console.print("-" * max(console.width - 1, 1))
    console.print()
