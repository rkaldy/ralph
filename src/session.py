import re
import sys
import tomllib
from pathlib import Path
from types import TracebackType

from openai_codex import Codex, Sandbox, SkillInput, TextInput, Thread
from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    AgentMessageThreadItem,
    CommandExecutionThreadItem,
    ItemCompletedNotification,
    ItemStartedNotification,
    MessagePhase,
    ReasoningSummaryTextDeltaNotification,
    ReasoningTextDeltaNotification,
    ReasoningThreadItem,
    TurnCompletedNotification,
    TurnStatus,
)
from pydantic import BaseModel, ValidationError
from rich.syntax import Syntax
from rich.text import Text

from exceptions import RalphError
from ui import LiveRow, console

CODEX_CONFIG_PATH = Path.home() / ".codex/config.toml"
COMPLETE_MARKER = "<COMPLETE>"
AGENT_INITIAL_BUFFERING = len(COMPLETE_MARKER) + 3
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
            config=(
                {
                    "model_reasoning_effort": self.reasoning,
                    "model_reasoning_summary": "auto",
                }
                if self.reasoning is not None
                else {"model_reasoning_summary": "auto"}
            ),
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

    @staticmethod
    def _format_command(command: str) -> Text:
        if match := re.fullmatch(r'/bin/bash\s+-[^\s"]+\s+["\'](.*)["\']', command, flags=re.DOTALL):
            command = match.group(1)
        return Syntax("", "bash", theme="monokai").highlight(command)

    def prompt(self, prompt: str) -> bool:
        if self.thread is None:
            raise RalphError("Codex session is not started")

        turn = self.thread.turn(
            [TextInput(text=prompt), SkillInput(name=self.skill, path=str(self._skill_path()))],
        )

        complete: bool = False
        reasoning_has_delta = False
        row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
        try:
            for event in turn.stream():
                payload = event.payload
                # console.print(event.method, style="#808080")
                if isinstance(payload, ItemStartedNotification):
                    item = payload.item.root
                    if isinstance(item, AgentMessageThreadItem):
                        row.start("")
                    elif isinstance(item, ReasoningThreadItem):
                        reasoning_has_delta = True
                        row.start("", style="reasoning")
                    elif isinstance(item, CommandExecutionThreadItem):
                        row.text(
                            Text.from_markup("[green][bold]Run[/] ").append_text(
                                self._format_command(item.command)
                            )
                        )
                        row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
                elif isinstance(payload, AgentMessageDeltaNotification):
                    if row.match(COMPLETE_MARKER):
                        complete = True
                    if not complete:
                        row.update(payload.delta)
                elif isinstance(
                    payload,
                    (ReasoningSummaryTextDeltaNotification, ReasoningTextDeltaNotification),
                ):
                    row.update(payload.delta)
                elif isinstance(payload, ItemCompletedNotification):
                    item = payload.item.root
                    if isinstance(item, AgentMessageThreadItem):
                        row.stop()
                        if COMPLETE_MARKER in item.text:
                            complete = True
                        if item.phase != MessagePhase.final_answer:
                            console.print()
                            row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
                    elif isinstance(item, ReasoningThreadItem):
                        if not reasoning_has_delta:
                            reasoning_text = "\n".join(item.summary or item.content or [])
                            if reasoning_text:
                                row.update(reasoning_text)
                        row.stop()
                        console.print()
                        row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
                elif isinstance(payload, TurnCompletedNotification):
                    if payload.turn.status == TurnStatus.interrupted:
                        raise RalphError("Interrupted")
                    elif payload.turn.status == TurnStatus.failed:
                        raise RalphError(payload.turn.error)
        finally:
            row.stop()

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
