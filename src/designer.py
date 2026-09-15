from pathlib import Path

import typer
from openai_codex import CodexError

import ui
from codex import CodexSession, RalphError
from config import RalphConfig
from ui import INTRO_BRIGHT


class Designer:
    def __init__(self, config: RalphConfig):
        self.config = config
        self.ralph_dir = Path.cwd() / ".ralph"

    def design(self, feature: str) -> None:
        ui.intro(
            "Project Requirement Description session",
            self.config.GPT_MODEL_DESIGN,
            self.config.GPT_REASONING_DESIGN,
        )

        try:
            with CodexSession(
                "prd",
                model=self.config.GPT_MODEL_DESIGN,
                reasoning=self.config.GPT_REASONING_DESIGN,
            ) as session:
                response = session.prompt(
                    f"Make an interactive user session for creating a PRD for this feature: {feature}"
                )
                while True:
                    if response.completed:
                        typer.echo(
                            typer.style("Design session completed. The generated PRD is at ", fg=INTRO_BRIGHT)
                            + typer.style(response.file, fg=INTRO_BRIGHT, bold=True)
                            + typer.style(" .\nReview and update it and then run ", fg=INTRO_BRIGHT)
                            + typer.style(f"ralph execute {response.file}", fg=INTRO_BRIGHT, bold=True)
                            + typer.style(" .\n", fg=INTRO_BRIGHT)
                        )
                        return

                    answer = ui.prompt_user()
                    response = session.prompt(answer)

        except (CodexError, RalphError) as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(code=1) from error

    def convert(self, prd: Path) -> None:
        ui.intro(
            "PRD conversion",
            self.config.GPT_MODEL_DESIGN,
            self.config.GPT_REASONING_DESIGN,
        )

        output_path = self.ralph_dir / "prd.json"
        try:
            with CodexSession(
                "convert",
                model=self.config.GPT_MODEL_DESIGN,
                reasoning=self.config.GPT_REASONING_DESIGN,
            ) as session:
                response = session.prompt(f"Convert PRD at {prd} to {output_path}.")

            if not response.file or response.file.resolve() != output_path.resolve():
                raise RalphError("Codex did not complete the conversion to prd.json")

            typer.echo(
                typer.style("Conversion completed. The generated JSON PRD is at ", fg=INTRO_BRIGHT)
                + typer.style(output_path, fg=INTRO_BRIGHT, bold=True)
                + typer.style(" .\n", fg=INTRO_BRIGHT)
            )
        except (CodexError, RalphError) as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(code=1) from error
