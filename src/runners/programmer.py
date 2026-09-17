import subprocess
from enum import Enum
from pathlib import Path

import typer
from pydantic import Field
from rich.markdown import Markdown

import ui
from codex import CodexSession
from config import RalphConfig
from exceptions import RalphError
from models import PRD, CodexResultBase, Story
from runners.runner import CodexRunner


class ProgrammingResult(CodexResultBase):
    description: str = Field(description="Briefly explains what was implemented")
    files: list[str] = Field(description="Lists every changed file")
    patterns: list[str] = Field(description="Contains reusable codebase knowledge discovered during the work")
    gotchas: list[str] = Field(description="Contains pitfalls relevant to later iterations or stories")


class QA(Enum):
    LINT = "lint"
    TYPECHECK = "typecheck"
    TEST = "test"


class Programmer(CodexRunner):
    def __init__(self, config: RalphConfig):
        super().__init__(
            config,
            skill="programmer",
            title="Agentic programmer",
            gpt_model=config.GPT_MODEL_PROGRAMMER,
            reasoning=config.GPT_REASONING_PROGRAMMER,
        )
        self.max_iterations = config.MAX_ITERATIONS
        self.qa_commands = {
            QA.LINT: config.LINT_COMMAND,
            QA.TYPECHECK: config.TYPECHECK_COMMAND,
            QA.TEST: config.TEST_COMMAND,
        }

    def delete_qa_results(self) -> None:
        for qa in QA:
            (self.ralph_dir / f"{qa.value}-result.txt").unlink(missing_ok=True)

    def run_qa(self, name: str, command: str) -> bool:
        result_file = self.ralph_dir / f"{name}-result.txt"
        result_file.unlink(missing_ok=True)

        ui.console.print(f"\n[command]Run {name}[/command]: {command}\n")
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
            self.run_qa(name.value, command)
            for name, command in self.qa_commands.items()
            if command is not None
        ]
        return all(results)

    def build_prompt(self, story: Story, iteration_num: int) -> str:
        if iteration_num == 1:
            prompt = (
                f"Implement the following user story: {story.title}\n\n"
                + f"Description: {story.description}\n\n"
            )
        else:
            prompt = f"Fix errors in the implementation of the user story: {story.title}\n\n"
            for qa in QA:
                if (qa_result := self.ralph_dir / f"{qa.value}-result.txt").is_file():
                    prompt += (
                        f"The {qa.value} checker found errors, its output is stored "
                        f"in the file `{qa_result}`.\n"
                    )
            prompt += "\n"
        prompt += "Acceptance criteria:\n" + "\n".join([f" - {ac}" for ac in story.acceptance_criteria])
        return prompt

    def update_progress(self, story: Story, result: ProgrammingResult) -> None:
        summary = (
            f"## {story.id}: {story.title}\n\n{result.description}\n\n"
            f"### Files changed\n\n{'\n'.join(f'- {path}' for path in result.files)}\n\n"
            f"### Codebase Patterns\n\n{'\n'.join(f'- {pattern}' for pattern in result.patterns)}\n\n"
            f"### Gotchas encountered\n\n{'\n'.join(f'- {gotcha}' for gotcha in result.gotchas)}\n\n"
        )
        ui.console.print(Markdown(summary, style="prompt"))
        with self.progress_file.open("a", encoding="utf-8") as progress:
            progress.write(summary)

    def do_iteration(self, session: CodexSession, story: Story, iteration_num: int) -> bool:
        ui.horizontal_line()
        ui.console.print(
            f"Story: [bold]{story.title}[/bold]  iteration: [bold]{iteration_num}[/bold]\n",
            style="meta",
        )

        prompt = self.build_prompt(story, iteration_num)
        ui.console.print(f"[bold]Prompt:[/bold]\n{prompt}\n", style="prompt")
        if not session.prompt(prompt):
            raise RalphError("The story is a blocker")
        return self.run_quality_checks()

    def do_story(self, story: Story) -> None:
        self.delete_qa_results()
        with self.session as session:
            iteration_num = 1
            while not self.do_iteration(session, story, iteration_num):
                iteration_num += 1
                if iteration_num > self.max_iterations:
                    raise RalphError(f"Number of iterations exceeded {self.max_iterations}")

            self.update_progress(story, session.summary(ProgrammingResult))
            story.passes = True
            self.prd_file.write_text(self.prd.model_dump_json(indent=2))
            ui.console.print(f"Story [bold]{story.title}[/bold] completed\n", style="meta")

    def run(self) -> None:
        self.intro()
        try:
            self.prd_file = self.ralph_dir / "prd.json"
            self.progress_file = self.ralph_dir / "progress.md"
            self.prd = PRD.model_validate_json(self.prd_file.read_text(encoding="utf-8"))
            self.progress_file.write_text("", encoding="utf-8")

            while (story := self.prd.next_story()) is not None:
                self.do_story(story)

        except Exception as error:
            typer.secho(f"Error: {error}", err=True, fg=typer.colors.BRIGHT_RED)
            raise typer.Exit(code=1) from error
