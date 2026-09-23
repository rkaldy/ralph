from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai_codex import SkillInput, TextInput
from openai_codex.generated.v2_all import (
    AgentMessageThreadItem,
    ItemCompletedNotification,
    MessagePhase,
    ThreadItem,
)
from pytest_mock import MockerFixture

from ralph.ui import LinePreservingMarkdown


def codex_session_mock(mocker: MockerFixture, behavior: Callable[[str], str | None]):
    thread_class_mock = mocker.patch("ralph.codex.Thread", autospec=True)
    thread_mock = thread_class_mock.return_value
    codex_class_mock = mocker.patch("ralph.codex.Codex", autospec=True)
    codex_mock = codex_class_mock.return_value
    codex_mock.thread_start.return_value = thread_mock

    def run_turn(inputs: list[TextInput | SkillInput]) -> MagicMock:
        turn = MagicMock()
        turn.stream.return_value = []
        if isinstance(inputs[0], TextInput):
            output = behavior(inputs[0].text)
            if output:
                completed_item = AgentMessageThreadItem(
                    id="item1",
                    phase=MessagePhase.final_answer,
                    text=output,
                    type="agentMessage",
                )
                completed_event = SimpleNamespace(
                    payload=ItemCompletedNotification(
                        completed_at_ms=0,
                        item=ThreadItem(root=completed_item),
                        thread_id="thread1",
                        turn_id="turn1",
                    )
                )
                turn.stream.return_value = [completed_event]
        return turn

    thread_mock.turn.side_effect = run_turn


@pytest.fixture
def live_mock(mocker: MockerFixture):
    live_class_mock = mocker.patch("ralph.ui.Live", autospec=True)
    return live_class_mock.return_value


@pytest.fixture
def console_mock(mocker: MockerFixture):
    mocker.patch("ralph.codex.console")
    console = mocker.patch("ralph.ui.console", autospec=True)
    console.width = 80
    return console


def assert_live_mock_writes(live_mock, lines: list[str]):
    updates = [call.args[0] for call in live_mock.update.call_args_list]
    assert all(isinstance(item, LinePreservingMarkdown) for item in updates)
    assert [item.markup for item in updates] == lines
