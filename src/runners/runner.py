import contextlib
from pathlib import Path

import typer
from rich.panel import Panel

import ui
from codex import CodexSession
from config import RalphConfig


class CodexRunner:
    def __init__(
        self, config: RalphConfig, skill: str, title: str, gpt_model: str | None, reasoning: str | None
    ) -> None:
        self.title = title
        self.session = CodexSession(config, skill, gpt_model, reasoning)
        self.ralph_dir = Path(".ralph")
        self.ralph_dir.mkdir(exist_ok=True)

    def intro(self) -> None:
        cwd = Path.cwd()
        with contextlib.suppress(BaseException):
            cwd = Path("~") / cwd.relative_to(Path.home())
        intro = (
            f"[metadark][bold]Ralph ◆[/] [meta]{self.title}[/meta]\n\n"
            f"[metadark]model:[/metadark] [meta]{self.session.model} {self.session.reasoning}\n"
            f"[metadark]directory:[/metadark] [meta]{cwd}"
        )
        ui.console.print(Panel(intro, border_style="metadark", padding=(0, 2)))
        ui.console.print()

    def prepare(self) -> None:
        pass

    def execute(self) -> None:
        pass

    def run(self) -> None:
        self.intro()
        try:
            self.prepare()
            with self.session:
                self.execute()
        except Exception as error:
            typer.secho(f"Error: {error}", err=True, fg=typer.colors.BRIGHT_RED)
            raise typer.Exit(code=1) from error
