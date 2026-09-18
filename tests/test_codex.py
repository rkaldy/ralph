import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai_codex import Sandbox, SkillInput, TextInput
from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    ItemCompletedNotification,
    ItemStartedNotification,
    TurnCompletedNotification,
)

import codex
from config import RalphConfig
from exceptions import RalphError


@pytest.fixture
def codex_mocks(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    factory = MagicMock(name="Codex")
    client = MagicMock(name="codex_client")
    factory.return_value = client
    monkeypatch.setattr(codex, "Codex", factory)
    return factory, client


def make_session(
    codex_mocks: tuple[MagicMock, MagicMock],
    *,
    skill: str = "test-skill",
    model: str | None = None,
    reasoning: str | None = None,
    show_commands: bool = False,
) -> codex.CodexSession:
    factory, _ = codex_mocks
    config = RalphConfig.model_construct(SHOW_COMMANDS=show_commands)
    session = codex.CodexSession(config, skill, model, reasoning)
    factory.assert_called_once_with()
    return session


@pytest.fixture
def fake_ui(monkeypatch: pytest.MonkeyPatch) -> tuple[type[Any], MagicMock]:
    class FakeLiveRow:
        instances: list["FakeLiveRow"] = []

        def __init__(self, initial_buffering: int = 0) -> None:
            self.initial_buffering = initial_buffering
            self.buffer = ""
            self.calls: list[tuple[Any, ...]] = []
            self.stop_count = 0
            self.__class__.instances.append(self)

        def start(self, delta: str, style: str | None = None) -> None:
            self.calls.append(("start", delta, style))
            self.buffer += delta

        def update(self, delta: str) -> None:
            self.calls.append(("update", delta))
            self.buffer += delta

        def text(self, value: Any) -> None:
            self.calls.append(("text", value))

        def stop(self) -> None:
            self.calls.append(("stop",))
            self.stop_count += 1

        def match(self, pattern: str) -> bool:
            return pattern in self.buffer

    console = MagicMock(name="console")
    monkeypatch.setattr(codex, "LiveRow", FakeLiveRow)
    monkeypatch.setattr(codex, "console", console)
    return FakeLiveRow, console


def event(payload: Any) -> SimpleNamespace:
    return SimpleNamespace(payload=payload)


def item_started(item: dict[str, Any]) -> SimpleNamespace:
    return event(ItemStartedNotification(item=item, started_at_ms=1, thread_id="thread", turn_id="turn"))


def item_completed(item: dict[str, Any]) -> SimpleNamespace:
    return event(ItemCompletedNotification(item=item, completed_at_ms=2, thread_id="thread", turn_id="turn"))


def agent_delta(delta: str) -> SimpleNamespace:
    return event(
        AgentMessageDeltaNotification(delta=delta, item_id="agent", thread_id="thread", turn_id="turn")
    )


def install_skill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    checkout_root = tmp_path / "checkout"
    skill_path = checkout_root / "skills/test-skill/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Test skill\n", encoding="utf-8")
    monkeypatch.setattr(codex, "__file__", str(checkout_root / "src/codex.py"))
    return skill_path.resolve()


def prepare_stream(session: codex.CodexSession, events: Any) -> MagicMock:
    thread = MagicMock(name="thread")
    turn = MagicMock(name="turn")
    turn.stream.return_value = events
    thread.turn.return_value = turn
    session.thread = thread
    return thread


def test_context_manager_enters_and_exits_codex(codex_mocks: tuple[MagicMock, MagicMock]) -> None:
    _, client = codex_mocks
    session = make_session(codex_mocks)

    with session as entered_session:
        assert entered_session is session

    client.__enter__.assert_called_once_with()
    client.__exit__.assert_called_once_with(None, None, None)


def test_skill_path_prefers_checkout_skill(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_skill = checkout_root / "skills/test-skill/SKILL.md"
    checkout_skill.parent.mkdir(parents=True)
    checkout_skill.write_text("checkout", encoding="utf-8")
    installed_prefix = tmp_path / "prefix"
    installed_skill = installed_prefix / "share/ralph/skills/test-skill/SKILL.md"
    installed_skill.parent.mkdir(parents=True)
    installed_skill.write_text("installed", encoding="utf-8")
    monkeypatch.setattr(codex, "__file__", str(checkout_root / "src/codex.py"))
    monkeypatch.setattr(sys, "prefix", str(installed_prefix))
    session = make_session(codex_mocks)

    assert session._skill_path() == checkout_skill.resolve()


def test_skill_path_falls_back_to_installed_skill(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout_root = tmp_path / "checkout"
    installed_prefix = tmp_path / "prefix"
    installed_skill = installed_prefix / "share/ralph/skills/test-skill/SKILL.md"
    installed_skill.parent.mkdir(parents=True)
    installed_skill.write_text("installed", encoding="utf-8")
    monkeypatch.setattr(codex, "__file__", str(checkout_root / "src/codex.py"))
    monkeypatch.setattr(sys, "prefix", str(installed_prefix))
    session = make_session(codex_mocks)

    assert session._skill_path() == installed_skill.resolve()


def test_skill_path_raises_when_skill_is_not_installed(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(codex, "__file__", str(tmp_path / "checkout/src/codex.py"))
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "prefix"))
    session = make_session(codex_mocks, skill="missing")

    with pytest.raises(RalphError, match="'missing' skill is not installed"):
        session._skill_path()


@pytest.mark.parametrize(
    ("reasoning", "expected_config"),
    [
        ("high", {"model_reasoning_effort": "high", "model_reasoning_summary": "auto"}),
        (None, {"model_reasoning_summary": "auto"}),
    ],
)
def test_start_thread_stores_thread_and_supplies_configuration(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reasoning: str | None,
    expected_config: dict[str, str],
) -> None:
    _, client = codex_mocks
    monkeypatch.chdir(tmp_path)
    session = make_session(codex_mocks, model="test-model", reasoning=reasoning)
    thread = MagicMock(name="thread")
    client.thread_start.return_value = thread

    session.start_thread()

    assert session.thread is thread
    client.thread_start.assert_called_once_with(
        cwd=str(tmp_path),
        sandbox=Sandbox.workspace_write,
        model="test-model",
        config=expected_config,
    )


def test_prompt_raises_before_thread_start(codex_mocks: tuple[MagicMock, MagicMock]) -> None:
    session = make_session(codex_mocks)

    with pytest.raises(RalphError, match="Codex thread not started"):
        session.prompt("hello")


def test_prompt_sends_text_and_resolved_skill_inputs(
    codex_mocks: tuple[MagicMock, MagicMock],
    fake_ui: tuple[type[Any], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected_skill_path = install_skill(monkeypatch, tmp_path)
    session = make_session(codex_mocks)
    thread = prepare_stream(session, [])
    row_type, _ = fake_ui

    assert session.prompt("Build the feature") is False

    inputs = thread.turn.call_args.args[0]
    assert inputs == [
        TextInput(text="Build the feature"),
        SkillInput(name="test-skill", path=str(expected_skill_path)),
    ]
    assert row_type.instances[-1].stop_count == 1


def test_prompt_forwards_agent_and_reasoning_streams_to_ui(
    codex_mocks: tuple[MagicMock, MagicMock],
    fake_ui: tuple[type[Any], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_skill(monkeypatch, tmp_path)
    session = make_session(codex_mocks)
    events = [
        item_started({"type": "agentMessage", "id": "agent-1", "text": "", "phase": "commentary"}),
        agent_delta("Working "),
        agent_delta("on it"),
        item_completed(
            {"type": "agentMessage", "id": "agent-1", "text": "Working on it", "phase": "commentary"}
        ),
        item_started({"type": "reasoning", "id": "reasoning", "summary": [], "content": []}),
        item_completed(
            {
                "type": "reasoning",
                "id": "reasoning",
                "summary": ["First thought", "Second thought"],
                "content": [],
            }
        ),
        item_started({"type": "agentMessage", "id": "agent-2", "text": "", "phase": "final_answer"}),
        agent_delta("Finished"),
        item_completed({"type": "agentMessage", "id": "agent-2", "text": "Finished", "phase": "final_answer"}),
    ]
    prepare_stream(session, events)
    row_type, console = fake_ui

    assert session.prompt("go") is False

    assert len(row_type.instances) == 3
    first, reasoning, final = row_type.instances
    assert first.calls == [
        ("start", "", None),
        ("update", "Working "),
        ("update", "on it"),
        ("stop",),
    ]
    assert reasoning.calls == [
        ("start", "", "reasoning"),
        ("update", "First thought\nSecond thought"),
        ("stop",),
    ]
    assert final.calls == [
        ("start", "", None),
        ("update", "Finished"),
        ("stop",),
        ("stop",),
    ]
    assert console.print.call_count == 2


@pytest.mark.parametrize("show_commands", [False, True])
def test_prompt_renders_commands_only_when_enabled(
    codex_mocks: tuple[MagicMock, MagicMock],
    fake_ui: tuple[type[Any], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    show_commands: bool,
) -> None:
    install_skill(monkeypatch, tmp_path)
    session = make_session(codex_mocks, show_commands=show_commands)
    command = {
        "type": "commandExecution",
        "id": "command",
        "command": "pwd",
        "commandActions": [],
        "cwd": str(tmp_path),
        "status": "inProgress",
    }
    prepare_stream(session, [item_started(command)])
    rendered_command = object()
    format_command = MagicMock(name="format_command", return_value=rendered_command)
    monkeypatch.setattr(codex, "format_command", format_command)
    row_type, _ = fake_ui

    assert session.prompt("go") is False

    if show_commands:
        format_command.assert_called_once()
        assert len(row_type.instances) == 2
        assert ("text", rendered_command) in row_type.instances[0].calls
    else:
        format_command.assert_not_called()
        assert len(row_type.instances) == 1
        assert not any(call[0] == "text" for call in row_type.instances[0].calls)


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        ([agent_delta("ordinary output")], False),
        ([agent_delta("done <COMPLETE>")], True),
        (
            [
                item_completed(
                    {
                        "type": "agentMessage",
                        "id": "agent",
                        "text": "done <COMPLETE>",
                        "phase": "final_answer",
                    }
                )
            ],
            True,
        ),
    ],
)
def test_prompt_detects_completion_marker_in_streamed_or_completed_output(
    codex_mocks: tuple[MagicMock, MagicMock],
    fake_ui: tuple[type[Any], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    events: list[SimpleNamespace],
    expected: bool,
) -> None:
    install_skill(monkeypatch, tmp_path)
    session = make_session(codex_mocks)
    prepare_stream(session, events)

    assert session.prompt("go") is expected


@pytest.mark.parametrize(
    ("status", "error", "message"),
    [
        ("interrupted", None, "Interrupted"),
        ("failed", {"message": "model unavailable", "additionalDetails": "retry later"}, "model unavailable"),
    ],
)
def test_prompt_raises_meaningful_error_for_unsuccessful_turn(
    codex_mocks: tuple[MagicMock, MagicMock],
    fake_ui: tuple[type[Any], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
    error: dict[str, str] | None,
    message: str,
) -> None:
    install_skill(monkeypatch, tmp_path)
    session = make_session(codex_mocks)
    notification = TurnCompletedNotification(
        thread_id="thread",
        turn={"id": "turn", "items": [], "status": status, "error": error},
    )
    prepare_stream(session, [event(notification)])

    with pytest.raises(RalphError, match=message):
        session.prompt("go")


def test_prompt_stops_active_row_when_stream_raises_without_swallowing_exception(
    codex_mocks: tuple[MagicMock, MagicMock],
    fake_ui: tuple[type[Any], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_skill(monkeypatch, tmp_path)
    session = make_session(codex_mocks)
    original = RuntimeError("stream disconnected")

    def broken_stream() -> Any:
        yield agent_delta("partial")
        raise original

    prepare_stream(session, broken_stream())
    row_type, _ = fake_ui

    with pytest.raises(RuntimeError, match="stream disconnected") as caught:
        session.prompt("go")

    assert caught.value is original
    assert row_type.instances[-1].stop_count == 1
