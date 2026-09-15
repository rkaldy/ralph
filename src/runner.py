import contextlib
from pathlib import Path

import typer

import ui
from config import RalphConfig
from session import CodexSession


class CodexRunner:
    def __init__(
        self, config: RalphConfig, skill: str, title: str, gpt_model: str | None, reasoning: str | None
    ) -> None:
        self.config = config
        self.skill = skill
        self.ralph_dir = Path.cwd() / ".ralph"
        self.title = title
        self.gpt_model = gpt_model
        self.reasoning = reasoning

    def run(self) -> None:
        directory = Path.cwd()
        with contextlib.suppress(BaseException):
            directory = Path("~") / directory.relative_to(Path.home())
        ui.intro(self.title, self.gpt_model, self.reasoning, str(directory))

        try:
            self.prepare()
            with CodexSession(skill=self.skill, model=self.gpt_model, reasoning=self.reasoning) as session:
                self.execute(session)
        except Exception as error:
            typer.secho(f"Error: {error}", err=True, fg=typer.colors.BRIGHT_RED)
            raise typer.Exit(code=1) from error

    def prepare(self) -> None:
        pass

    def execute(self, session: CodexSession) -> None:
        pass
