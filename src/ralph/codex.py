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
    ReasoningThreadItem,
    TurnCompletedNotification,
    TurnStatus,
)
from pydantic import BaseModel, ValidationError

from ralph.config import RalphConfig
from ralph.exceptions import RalphError
from ralph.ui import LiveRow, console, format_command

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
        config: RalphConfig,
        skill: str,
        model: str | None = None,
        reasoning: str | None = None,
    ):
        self.codex = Codex()
        self.thread: Thread | None = None
        self.skill = skill
        self.model = model or None
        self.reasoning = reasoning or None
        self.show_commands = config.SHOW_COMMANDS

    def __enter__(self) -> "CodexSession":
        self.codex.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.codex.__exit__(exc_type, exc_val, exc_tb)

    def _skill_path(self) -> Path:
        path = Path(__file__).resolve().parent / "skills" / self.skill / "SKILL.md"
        if path.is_file():
            return path
        raise RalphError(f"'{self.skill}' skill is not installed")

    def start_thread(self) -> None:
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

    def prompt(self, prompt: str) -> bool:
        if self.thread is None:
            raise RalphError("Codex thread not started")

        turn = self.thread.turn(
            [TextInput(text=prompt), SkillInput(name=self.skill, path=str(self._skill_path()))],
        )

        complete: bool = False
        row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
        try:
            for event in turn.stream():
                payload = event.payload
                if isinstance(payload, ItemStartedNotification):
                    item = payload.item.root
                    if isinstance(item, AgentMessageThreadItem):
                        row.start("")
                    elif isinstance(item, ReasoningThreadItem):
                        row.start("", style="reasoning")
                    elif isinstance(item, CommandExecutionThreadItem) and self.show_commands:
                        row.text(format_command(item))
                        row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
                elif isinstance(payload, AgentMessageDeltaNotification):
                    row.update(payload.delta)
                    if row.match(COMPLETE_MARKER):
                        complete = True
                        row.stop()
                elif isinstance(payload, ItemCompletedNotification):
                    item = payload.item.root
                    if isinstance(item, AgentMessageThreadItem):
                        row.finish(item.text)
                        if COMPLETE_MARKER in item.text:
                            complete = True
                        if item.phase != MessagePhase.final_answer:
                            console.print()
                            row = LiveRow(initial_buffering=AGENT_INITIAL_BUFFERING)
                    elif isinstance(item, ReasoningThreadItem):
                        row.finish("\n".join(item.summary or item.content or []))
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
            raise RalphError("Codex thread not started")

        result = self.thread.run(
            [TextInput(text=SUMMARY_PROMPT)],
            output_schema=response_model.model_json_schema(),
        )
        if result.status == TurnStatus.failed:
            raise RalphError(result.error)
        if not result.final_response:
            raise RalphError("Codex returned no final response")
        try:
            return response_model.model_validate_json(result.final_response)
        except ValidationError as error:
            raise RalphError(f"Codex returned an invalid structured response: {error}") from error
