import subprocess
from enum import Enum
from pathlib import Path

import typer

import ui
from config import RalphConfig
from exceptions import RalphError
from git import commit_story, prepare_branch
from models import PRD, Story
from runners.runner import CodexRunner

PROGRESS_PROMPT = """
Update `.ralph/progress.md` with the new codebase pattens and gotchas, you just have discovered in this thread.
Codebase pattern is a reusable codebase knowledge discovered during your work in this thread. 
Gotcha is a pitfall relavant to later iteratins, stories or features.
Rules:
 - Every codebase pattern is an item in a bullet list in "Codebase Patterns" chapter.
 - Every gotcha is an item in a bullet list in "Gotchas Encountered" chapter.
 - Be strict. Use only pattern and gotchas that are important even outside the current story. It's ok you don't 
   have any pattern or gotcha for this story. The `progess.md` should not bloat with minor pattens. 
 - Do not duplicate patterns and gotchas. If there is a similar pattern or gotcha in the `progress.md`, don't
   add anything.
 - Do not modify any other chapters than "Codebase Patterns" and "Gotchas Encountered".
"""


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
        self.first = True
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
        results = [self.run_qa(name.value, command) for name, command in self.qa_commands.items() if command]
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

    def do_iteration(self, story: Story, iteration_num: int) -> bool:
        if not self.first:
            ui.console.print("─" * max(ui.console.width - 1, 1), style="metadark")
            ui.console.print()
        self.first = False
        ui.console.print(
            f"[bold]{story.id}: {story.title}[/bold] "
            + f"[metadark]◆[/metadark] iteration [bold]#{iteration_num}[/bold]\n",
            style="meta",
            highlight=False,
        )

        prompt = self.build_prompt(story, iteration_num)
        ui.console.print(f"{prompt}\n", style="prompt")
        self.session.prompt(prompt)

        return self.run_quality_checks()

    def do_story(self, story: Story) -> None:
        self.delete_qa_results()
        self.session.start_thread()
        iteration_num = 1
        while not self.do_iteration(story, iteration_num):
            iteration_num += 1
            if iteration_num > self.max_iterations:
                raise RalphError(f"Number of iterations exceeded {self.max_iterations}")

        ui.console.print("\nUpdating progress.md\n", style="meta")
        self.session.prompt(PROGRESS_PROMPT)
        story.passes = True
        self.prd_file.write_text(self.prd.model_dump_json(indent=2))
        commit_story(story.title)
        ui.console.print(f"\nStory [bold]{story.title}[/bold] completed\n", style="meta", highlight=False)

    def prepare(self) -> None:
        self.prd_file = self.ralph_dir / "prd.json"
        self.prd = PRD.model_validate_json(self.prd_file.read_text(encoding="utf-8"))
        prepare_branch(self.prd.branch_name)
        ui.console.print(
            f"Using Git branch [bold]{self.prd.branch_name}[/bold]\n", style="meta", highlight=False
        )

    def execute(self) -> None:
        if (stories_passed := self.prd.num_passed_stories()) > 0:
            ui.console.print(
                f"Ralph have already completed {stories_passed} stories. Resuming with the rest.\n",
                style="meta",
                highlight=False,
            )
        while (story := self.prd.next_story()) is not None:
            self.do_story(story)
