import sys
import tomllib
from pathlib import Path
from types import TracebackType

import typer
from openai_codex import Codex, Sandbox, SkillInput, TextInput, Thread
from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    AgentMessageThreadItem,
    CommandExecutionOutputDeltaNotification,
    ItemCompletedNotification,
    ItemStartedNotification,
    MessagePhase,
    TurnCompletedNotification,
    TurnStatus,
)
from pydantic import BaseModel, ValidationError

from exceptions import RalphError
from stream import CodexStreamOutput

CODEX_CONFIG_PATH = Path.home() / ".codex/config.toml"

COMPLETE_MARKER = "<COMPLETE>"
SUMMARY_PROMPT = """
Report the outcome of the thread using the supplied output schema.
This is a read-only reporting turn:
  - Do not continue or redo the work.
  - Do not modify files or execute commands.
  - Report only actions, results, and artifacts actually produced by this thread.
  - Do not infer success from plans, intentions, or expected output paths.
  - Use null or empty collections when optional information is unavailable.
  - Return no user-facing explanation; the result is consumed by the orchestrator.
"""


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

    def prompt(self, prompt: str) -> bool:
        if self.thread is None:
            raise RalphError("Codex session is not started")

        turn = self.thread.turn(
            [TextInput(text=prompt), SkillInput(name=self.skill, path=str(self._skill_path()))],
        )

        complete: bool = False
        hidden_items: set[str] = set()
        output = CodexStreamOutput()
        for event in turn.stream():
            payload = event.payload
            if isinstance(payload, ItemStartedNotification):
                item = payload.item.root
                if isinstance(item, AgentMessageThreadItem):
                    if item.phase == MessagePhase.final_answer:
                        hidden_items.add(item.id)
                    else:
                        typer.echo("• ", nl=False)
            elif isinstance(payload, AgentMessageDeltaNotification):
                if payload.item_id not in hidden_items:
                    output.write(payload.delta, AgentMessageDeltaNotification)
            elif isinstance(payload, CommandExecutionOutputDeltaNotification):
                output.write(payload.delta, CommandExecutionOutputDeltaNotification)
            elif isinstance(payload, ItemCompletedNotification):
                item = payload.item.root
                if isinstance(item, AgentMessageThreadItem):
                    if item.phase == MessagePhase.final_answer:
                        if COMPLETE_MARKER in item.text:
                            complete = True
                        else:
                            output.write(item.text, AgentMessageDeltaNotification)
                    typer.echo("\n")
            elif isinstance(payload, TurnCompletedNotification):
                if payload.turn.status == TurnStatus.interrupted:
                    raise RalphError("Interrupted")
                elif payload.turn.status == TurnStatus.failed:
                    raise RalphError(payload.turn.error)

        return complete

    def summary[ResponseT: BaseModel](self, response_model: type[ResponseT]) -> ResponseT:
        if self.thread is None:
            raise RalphError("Codex session is not started")

        result = self.thread.run(
            [TextInput(text=SUMMARY_PROMPT), SkillInput(name=self.skill, path=str(self._skill_path()))],
            output_schema=response_model.model_json_schema(),
        )
        if result.status == TurnStatus.failed or not result.final_response:
            raise RalphError(result.error)
        try:
            return response_model.model_validate_json(result.final_response)
        except ValidationError as error:
            raise RalphError(f"Codex returned an invalid structured response: {error}") from error
