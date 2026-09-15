import re
import sys
import tomllib
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

from openai_codex import Codex, InputItem, Sandbox, SkillInput, TextInput, Thread
from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    CommandExecutionOutputDeltaNotification,
    TurnCompletedNotification,
    TurnStatus,
)

import ui
from stream import CodexStreamOutput

CODEX_CONFIG_PATH = Path.home() / ".codex/config.toml"
COMPLETION_PATTERN = re.compile(r"<!-- ralph:complete path=(?P<path>.+?) -->")


@dataclass
class CodexResponse:
    text: str
    completed: bool
    file: Path | None = None


class RalphError(Exception):
    pass


class CodexSession:
    def __init__(
        self,
        skill: str,
        model: str | None = None,
        reasoning: str | None = None,
    ):
        self.codex = Codex()
        self.thread: Thread | None = None
        self.skill = skill
        self.model = model or None
        self.reasoning = reasoning or None
        self.first = True

    def __enter__(self) -> "CodexSession":
        self.codex.__enter__()
        self.thread = self.codex.thread_start(
            cwd=str(Path.cwd()),
            sandbox=Sandbox.workspace_write,
            model=self.model,
            config=({"model_reasoning_effort": self.reasoning} if self.reasoning is not None else None),
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.codex.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def model_settings() -> tuple[str | None, str | None]:
        """Load model settings from the user's Codex configuration."""
        try:
            with CODEX_CONFIG_PATH.open("rb") as config_file:
                config = tomllib.load(config_file)
        except OSError:
            return None, None

        model = config.get("model")
        reasoning = config.get("model_reasoning_effort")
        return (
            model if isinstance(model, str) and model else None,
            reasoning if isinstance(reasoning, str) and reasoning else None,
        )

    def _skill_path(self) -> Path:
        checkout_skill = Path(__file__).resolve().parent.parent / f"skills/{self.skill}/SKILL.md"
        installed_skill = Path(sys.prefix) / f"share/ralph/skills/{self.skill}/SKILL.md"
        for path in (checkout_skill, installed_skill):
            if path.is_file():
                return path.resolve()
        raise RalphError(f"'{self.skill}' skill is not installed")

    def _build_response(self, result: str) -> CodexResponse:
        cwd = Path.cwd()

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
                    raise RalphError(f"Codex did not create {response.file}")
                try:
                    absolute_path.relative_to(cwd.resolve())
                except ValueError as error:
                    raise RalphError(f"Codex returned a path outside the project: {response.file}") from error

        return response

    def prompt(self, prompt: str) -> CodexResponse:
        input: list[InputItem] = [TextInput(text=prompt)]
        if self.first:
            self.first = False
            input.append(SkillInput(name=self.skill, path=str(self._skill_path())))
        if self.thread is None:
            raise RalphError("Codex session is not started")

        turn = self.thread.turn(input)
        output = CodexStreamOutput()
        last_agent_item_id: str | None = None

        waiting = ExitStack()
        waiting.enter_context(ui.codex_spinner())
        try:
            for event in turn.stream():
                payload = event.payload
                if isinstance(payload, AgentMessageDeltaNotification):
                    waiting.close()
                    if payload.item_id != last_agent_item_id:
                        output.write_separator()
                    last_agent_item_id = payload.item_id
                    output.write(payload.delta, type(payload))
                elif isinstance(payload, CommandExecutionOutputDeltaNotification):
                    waiting.close()
                    output.write(payload.delta, type(payload))
                elif isinstance(payload, TurnCompletedNotification):
                    if payload.turn.status == TurnStatus.failed:
                        raise RalphError(payload.turn.error)
        finally:
            waiting.close()
            output.finish()

        result = output.result
        if not result:
            raise RalphError("Codex returned an empty response")
        return self._build_response(result)
