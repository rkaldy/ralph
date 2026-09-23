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

from ralph.config import RalphConfig
from ralph.exceptions import RalphError
from ralph.ui import LiveRow, console, format_command


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

    def prompt(self, prompt: str) -> None:
        if self.thread is None:
            raise RalphError("Codex thread not started")

        turn = self.thread.turn(
            [TextInput(text=prompt), SkillInput(name=self.skill, path=str(self._skill_path()))],
        )

        row = LiveRow()
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
                        row = LiveRow()
                elif isinstance(payload, AgentMessageDeltaNotification):
                    row.update(payload.delta)
                elif isinstance(payload, ItemCompletedNotification):
                    item = payload.item.root
                    if isinstance(item, AgentMessageThreadItem):
                        row.finish(item.text)
                        if item.phase != MessagePhase.final_answer:
                            console.print()
                            row = LiveRow()
                    elif isinstance(item, ReasoningThreadItem):
                        row.finish("\n".join(item.summary or item.content or []))
                        console.print()
                        row = LiveRow()
                elif isinstance(payload, TurnCompletedNotification):
                    if payload.turn.status == TurnStatus.interrupted:
                        raise RalphError("Interrupted")
                    elif payload.turn.status == TurnStatus.failed:
                        raise RalphError(payload.turn.error)
        finally:
            row.finish("")
