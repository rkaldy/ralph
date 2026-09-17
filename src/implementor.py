import subprocess
from pathlib import Path

import typer
from pydantic import Field

import ui
from config import RalphConfig
from exceptions import RalphError
from models import PRD, CodexResultBase, Story
from runner import CodexRunner
from session import CodexSession


class ExecutionResult(CodexResultBase):
    description: str = Field(description="Briefly explains what was implemented")
    files: list[str] = Field(description="Lists every changed file")
    patterns: list[str] = Field(description="Contains reusable codebase knowledge discovered during the work")
    gotchas: list[str] = Field(description="Contains pitfalls relevant to later iterations or stories")
    blocker: str | None = Field(
        description="Contains the reason the story cannot be implemented safely; otherwise leave it None"
    )


class Implementor(CodexRunner):
    def __init__(self, config: RalphConfig):
        super().__init__(
            config,
            skill="implement",
            title="Agentic coding",
            gpt_model=config.GPT_MODEL_IMPLEMENT,
            reasoning=config.GPT_REASONING_IMPLEMENT,
        )

    def delete_qa_results(self) -> None:
        for qa in ("lint", "typecheck", "test"):
            (self.ralph_dir / f"{qa}-result.txt").unlink(missing_ok=True)

    def run_qa(self, name: str, command: str) -> bool:
        if not command:
            return True

        result_file = self.ralph_dir / f".{name}-result.txt"
        result_file.unlink(missing_ok=True)

        ui.console.print(f"\n• Running {name}: {command}\n", style="meta")

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
        ui.console.print(f"Story: [bold]{story.title}[/bold]  iteration #{iteration_num}", style="meta")

        prompt = (
            "Implement the following user story:\n\n"
            + f"{story.title}\n\n"
            + f"Description: {story.description}\n\n"
            + f"Original PRD for global context: {self.prd.original_prd}\n\n"
            + "Acceptance criteria:\n"
            + "\n".join([f" - {ac}" for ac in story.acceptance_criteria])
        )
        session.prompt(prompt)
        summary = session.summary(ExecutionResult)
        if summary.blocker:
            raise RalphError(f"The story is a blocker: {summary.blocker}")
        return self.run_quality_checks()

    def prepare(self) -> None:
        self.prd_file = self.ralph_dir / "prd.json"
        self.progress_file = self.ralph_dir / "progress.md"

        self.prd = PRD.model_validate_json(self.prd_file.read_text(encoding="utf-8"))
        self.progress_file.write_text("", encoding="utf-8")

    def execute(self, session: CodexSession) -> None:
        while (story := self.prd.next_story()) is not None:
            success = False
            num_iterations = 0
            self.delete_qa_results()
            while not success:
                num_iterations += 1
                if num_iterations > self.config.MAX_ITERATIONS:
                    raise RalphError(f"Number of iterations exceeded {self.config.MAX_ITERATIONS}")
                success = self.iteration(session, story, num_iterations)

            ui.console.print(f"Story: [bold]{story.title}[/bold] completed\n", style="meta")
