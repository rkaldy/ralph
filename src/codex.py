import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from openai_codex import Codex, Sandbox, TextInput, SkillInput, Thread, RunInput

COMPLETION_PATTERN = re.compile(
    r"<!-- ralph:complete path=(?P<path>.+?) -->"
)

@dataclass
class CodexResponse:
    text: str
    completed: bool
    file: Path | None = None


class CodexException(Exception):
    pass


class CodexSession:
    def __init__(self, skill: str):
        self.codex = Codex()
        self.thread: Thread | None = None
        self.skill = skill
        self.first = True

    def skill_path(self) -> Path:
        checkout_skill = Path(__file__).resolve().parent.parent / f"skills/{self.skill}/SKILL.md"
        installed_skill = (
            Path(sys.prefix) / f"share/ralph/skills/{self.skill}/SKILL.md"
        )
        for path in (checkout_skill, installed_skill):
            if path.is_file():
                return path.resolve()
        raise CodexException(f"'{self.skill}' skill is not installed")

    def __enter__(self) -> "CodexSession":
        self.codex.__enter__()
        self.thread = self.codex.thread_start(
            cwd=str(Path.cwd()),
            sandbox=Sandbox.workspace_write,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.codex.__exit__(exc_type, exc_val, exc_tb)

    def prompt(self, prompt: str) -> CodexResponse:
        cwd = Path.cwd()

        input: RunInput = [TextInput(text=prompt)]
        if self.first:
            self.first = False
            input.append(SkillInput(name=self.skill, path=str(self.skill_path())))
        result = self.thread.run(input).final_response
        if not result:
            raise CodexException("Codex returned an empty response")

        completion = COMPLETION_PATTERN.search(result)
        response = CodexResponse(
            text=COMPLETION_PATTERN.sub("", result).strip(),
            completed=completion is not None,
        )
        if completion:
            response.file = Path(completion.group("path"))
            if response.file:
                absolute_path = (cwd / response.file).resolve()
                if not absolute_path.is_file():
                    raise CodexException(f"Codex did not create {response.file}")
                try:
                    absolute_path.relative_to(cwd.resolve())
                except ValueError as error:
                    raise CodexException(
                        f"Codex returned a path outside the project: {response.file}"
                    ) from error

        return response
