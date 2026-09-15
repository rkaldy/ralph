import subprocess
from pathlib import Path

import typer
from openai_codex import CodexError
from pydantic import ValidationError

import ui
from codex import CodexSession, RalphError
from config import RalphConfig
from models import PRD, ExecutionResult, Story
from ui import INTRO_BRIGHT


class Executor:
    def __init__(self, config: RalphConfig):
        self.config = config
        self.ralph_dir = Path.cwd() / ".ralph"

    def run_qa(self, name: str, command: str) -> bool:
        if not command:
            return True

        result_file = self.ralph_dir / f".{name}-result.txt"
        result_file.unlink(missing_ok=True)

        typer.secho(f"\n• Running {name}: {command}\n\n", fg=ui.COMMAND_OUTPUT)

        with (
            result_file.open("w", encoding="utf-8") as result_output,
            subprocess.Popen(
                command,
                cwd=Path.cwd(),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            ) as process,
        ):
            if process.stdout is None:
                raise RuntimeError(f"Could not capture output from {name}")
            for line in process.stdout:
                typer.echo(line, nl=False)
                result_output.write(line)
                result_output.flush()
            return_code = process.wait()

        if return_code == 0:
            result_file.unlink()
        return return_code == 0

    def run_quality_checks(self) -> bool:
        results = [
            self.run_qa("lint", self.config.LINT_COMMAND),
            self.run_qa("typecheck", self.config.TYPECHECK_COMMAND),
            self.run_qa("test", self.config.TEST_COMMAND),
        ]
        return all(results)

    def iteration(self, session: CodexSession, story: Story, iteration_num: int) -> bool:
        ui.horizontal_line()
        typer.echo(
            typer.style("Story: ", fg=INTRO_BRIGHT)
            + typer.style(story.title, fg=INTRO_BRIGHT, bold=True)
            + typer.style(f"  iteration #{iteration_num}\n\n", fg=INTRO_BRIGHT)
        )

        prompt = (
            "Implement the following user story:\n\n"
            + f"{story.title}\n\n"
            + f"Description: {story.description}\n\n"
            + "Acceptance criteria:\n"
            + "\n".join([f" - {ac}" for ac in story.acceptance_criteria])
        )
        response = session.prompt(prompt)
        result = ExecutionResult.model_validate_json(response.text)
        if result.blocker:
            raise RalphError(f"The story is a blocker: {result.blocker}")
        return self.run_quality_checks()

    def implement_story(self, session: CodexSession, story: Story) -> None:
        success = False
        num_iterations = 0
        for qa in ("lint", "typecheck", "test"):
            (Path.cwd() / f".ralph/{qa}-result.txt").unlink(missing_ok=True)
        while not success:
            num_iterations += 1
            if num_iterations > self.config.MAX_ITERATIONS:
                raise RalphError(f"Number of iterations exceeded {self.config.MAX_ITERATIONS}")
            success = self.iteration(session, story, num_iterations)
        typer.echo(
            typer.style("Story: ", fg=INTRO_BRIGHT)
            + typer.style(story.title, fg=INTRO_BRIGHT, bold=True)
            + typer.style(" completed", fg=INTRO_BRIGHT)
        )

    def run(self) -> None:
        ui.intro("Agentic coding", self.config.GPT_MODEL_EXECUTION, self.config.GPT_REASONING_EXECUTION)

        try:
            prd_file = self.ralph_dir / "prd.json"
            progress_file = self.ralph_dir / "progress.md"

            prd = PRD.model_validate_json(prd_file.read_text(encoding="utf-8"))
            progress_file.write_text("", encoding="utf-8")

            with CodexSession(
                "execute",
                model=self.config.GPT_MODEL_EXECUTION,
                reasoning=self.config.GPT_REASONING_EXECUTION,
            ) as session:
                while (story := prd.next_story()) is not None:
                    self.implement_story(session, story)
        except (OSError, UnicodeError, ValidationError, CodexError, RalphError) as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(code=1) from error
