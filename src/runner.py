import contextlib
from pathlib import Path

import typer
from rich.panel import Panel

import ui
from config import RalphConfig
from session import CodexSession


class CodexRunner:
    def __init__(
        self, config: RalphConfig, skill: str, title: str, gpt_model: str | None, reasoning: str | None
    ) -> None:
        self.config = config
        self.skill = skill
        self.ralph_dir = Path(".ralph")
        self.ralph_dir.mkdir(exist_ok=True)
        self.title = title
        self.gpt_model = gpt_model
        self.reasoning = reasoning

    def run(self) -> None:
        self._intro()
        try:
            self.prepare()
            with CodexSession(skill=self.skill, model=self.gpt_model, reasoning=self.reasoning) as session:
                self.execute(session)
        except Exception as error:
            typer.secho(f"Error: {error}", err=True, fg=typer.colors.BRIGHT_RED)
            raise typer.Exit(code=1) from error

    def _intro(self) -> None:
        cwd = Path.cwd()
        with contextlib.suppress(BaseException):
            cwd = Path("~") / cwd.relative_to(Path.home())
        intro = (
            f"[metadark][bold]Ralph ◆[/] [meta]{self.title}[/meta]\n\n"
            f"[metadark]model:[/metadark] [meta]{self.gpt_model} {self.reasoning}\n"
            f"[metadark]directory:[/metadark] [meta]{cwd}"
        )
        ui.console.print(Panel(intro, border_style="metadark", padding=(0, 2)))
        ui.console.print()

    def prepare(self) -> None:
        pass

    def execute(self, session: CodexSession) -> None:
        pass
