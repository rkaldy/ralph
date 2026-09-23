from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from openai_codex import Sandbox, SkillInput, TextInput
from openai_codex.generated.v2_all import (
    AgentMessageThreadItem,
    ItemCompletedNotification,
    MessagePhase,
    ThreadItem,
    TurnStatus,
)
from pytest_mock import MockerFixture

from ralph.codex import COMPLETE_MARKER, SUMMARY_PROMPT
from ralph.config import RalphConfig
from ralph.runners.designer import Designer, DesignResult


def test_designer_happy_path(
    mocker: MockerFixture,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    thread_class_mock = mocker.patch("ralph.codex.Thread", autospec=True)
    thread_mock = thread_class_mock.return_value
    codex_class_mock = mocker.patch("ralph.codex.Codex", autospec=True)
    codex_mock = codex_class_mock.return_value
    codex_mock.thread_start.return_value = thread_mock

    mocker.patch("ralph.ui.console", autospec=True)
    mocker.patch("ralph.codex.console", autospec=True)
    mocker.patch("ralph.codex.LiveRow", autospec=True)
    prompt_user_mock = mocker.patch(
        "ralph.ui.prompt_user",
        autospec=True,
        return_value="Store search filters",
    )

    prd_name = "saved-searches.md"
    prd_file = tmp_path / ".ralph" / "tasks" / prd_name
    completed_item = AgentMessageThreadItem(
        id="completed-design",
        phase=MessagePhase.final_answer,
        text=f"Created {prd_name}. {COMPLETE_MARKER}",
        type="agentMessage",
    )
    completed_event = SimpleNamespace(
        payload=ItemCompletedNotification(
            completed_at_ms=0,
            item=ThreadItem(root=completed_item),
            thread_id="designer-thread",
            turn_id="answer-turn",
        )
    )

    def run_turn(inputs: list[TextInput | SkillInput]) -> MagicMock:
        turn = MagicMock()
        if inputs[0] == TextInput(text="Store search filters"):
            prd_file.parent.mkdir(parents=True)
            prd_file.write_text("# PRD: Saved searches\n", encoding="utf-8")
            turn.stream.return_value = [completed_event]
        else:
            turn.stream.return_value = []
        return turn

    thread_mock.turn.side_effect = run_turn
    summary_result = MagicMock(
        status=TurnStatus.completed,
        final_response=DesignResult(prd_file=prd_name).model_dump_json(),
    )
    thread_mock.run.return_value = summary_result

    config = RalphConfig.model_construct(
        GPT_MODEL_DESIGNER="designer-model",
        GPT_REASONING_DESIGNER="high",
    )
    designer = Designer(config, "Add saved searches")

    designer.run()

    assert prd_file.is_file()
    codex_class_mock.assert_called_once_with()
    codex_mock.__enter__.assert_called_once_with()
    codex_mock.__exit__.assert_called_once_with(None, None, None)
    codex_mock.thread_start.assert_called_once_with(
        cwd=str(tmp_path),
        sandbox=Sandbox.workspace_write,
        model="designer-model",
        config={
            "model_reasoning_effort": "high",
            "model_reasoning_summary": "auto",
        },
    )
    assert [turn_call.args[0][0] for turn_call in thread_mock.turn.call_args_list] == [
        TextInput(
            text="Make an interactive user session for creating a PRD for this feature: Add saved searches"
        ),
        TextInput(text="Store search filters"),
    ]
    prompt_user_mock.assert_called_once_with()
    thread_mock.run.assert_called_once_with(
        [TextInput(text=SUMMARY_PROMPT)],
        output_schema=DesignResult.model_json_schema(),
    )
