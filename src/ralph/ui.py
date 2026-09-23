import re

import typer
from openai_codex.generated.v2_all import (
    CommandExecutionThreadItem,
    ListFilesCommandAction,
    ReadCommandAction,
    SearchCommandAction,
)
from rich.console import Console
from rich.control import Control
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

from ralph.exceptions import RalphError

theme = Theme(
    {
        "meta": "#ffe8c8",
        "metadark": "#807870",
        "command": "#50d050 bold",
        "user": "#ffffff on #202020",
        "reasoning": "#808080",
        "prompt": "#c0c0ff",
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
        self.stopped = False
        self.live.start()

    def text(self, text: Text) -> None:
        self.live.update(text)
        self.live.stop()

    def start(self, delta: str, style: str | None = None) -> None:
        if style:
            self.style = style
        self.update(delta)

    def update(self, delta: str) -> None:
        if self.stopped:
            return
        self.buffer += delta
        if len(self.buffer) > self.initial_buffering:
            self.live.update(LinePreservingMarkdown(self.buffer, style=self.style))

    def finish(self, text: str) -> None:
        if self.stopped:
            return
        self.live.update(LinePreservingMarkdown(text, style=self.style))
        self.live.stop()
        self.stopped = True

    def stop(self) -> None:
        self.live.stop()
        self.stopped = True

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


def format_command(item: CommandExecutionThreadItem) -> Text:
    ret = Text()
    for action in item.command_actions:
        root = action.root
        if isinstance(root, ReadCommandAction):
            cmd = Text.from_markup(f"[command]Read[/] {root.name}\n")
        elif isinstance(root, SearchCommandAction):
            cmd = Text.from_markup(f"[command]Search[/] {root.query or '?'} in {root.path or '?'}\n")
        elif isinstance(root, ListFilesCommandAction):
            cmd = Text.from_markup(f"[command]List[/] {root.path or '.'}\n")
        else:
            if match := re.fullmatch(r'/bin/bash\s+-[^\s"]+\s+["\'](.*)["\']', root.command, flags=re.DOTALL):
                command = match.group(1)
            else:
                command = root.command
            cmd = Text.from_markup("Run ", style="command").append_text(
                Syntax("", "bash", theme="fruity").highlight(f"{command}\n")
            )
        ret.append_text(cmd)
    return ret
