import json
import subprocess
from pathlib import Path
from unittest.mock import call

from openai_codex import Sandbox, TextInput
from pytest_mock import MockerFixture

from config import RalphConfig
from runners.programmer import PROGRESS_PROMPT, Programmer


class SuccessfulProcess:
    def __init__(self, output: str) -> None:
        self.stdout = iter([output])

    def __enter__(self) -> "SuccessfulProcess":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def wait(self) -> int:
        return 0


def test_programmer_happy_path(
    mocker: MockerFixture,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    prd_file = ralph_dir / "prd.json"
    prd_file.write_text(
        json.dumps(
            {
                "name": "Greeting",
                "branch_name": "greeting",
                "user_stories": [
                    {
                        "id": "US-001",
                        "title": "Add a greeting",
                        "description": "As a user, I want a greeting so that I feel welcome.",
                        "priority": 1,
                        "acceptance_criteria": ["Display a friendly greeting"],
                        "passes": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    thread_class_mock = mocker.patch("codex.Thread", autospec=True)
    thread_mock = thread_class_mock.return_value
    thread_mock.turn.return_value.stream.return_value = []
    codex_class_mock = mocker.patch("codex.Codex", autospec=True)
    codex_mock = codex_class_mock.return_value
    codex_mock.thread_start.return_value = thread_mock

    mocker.patch("ui.console", autospec=True)
    mocker.patch("codex.console", autospec=True)
    mocker.patch("codex.LiveRow", autospec=True)
    prepare_branch_mock = mocker.patch("runners.programmer.prepare_branch", autospec=True)
    commit_story_mock = mocker.patch("runners.programmer.commit_story", autospec=True)
    popen_mock = mocker.patch(
        "runners.programmer.subprocess.Popen",
        autospec=True,
        side_effect=[
            SuccessfulProcess("lint passed\n"),
            SuccessfulProcess("typecheck passed\n"),
            SuccessfulProcess("tests passed\n"),
        ],
    )

    config = RalphConfig.model_construct(
        LINT_COMMAND="lint-project",
        TYPECHECK_COMMAND="typecheck-project",
        TEST_COMMAND="test-project",
        SHOW_COMMANDS=False,
        MAX_ITERATIONS=3,
        GPT_MODEL_PROGRAMMER="programmer-model",
        GPT_REASONING_PROGRAMMER="high",
    )
    programmer = Programmer(config)

    programmer.run()

    codex_class_mock.assert_called_once_with()
    codex_mock.__enter__.assert_called_once_with()
    codex_mock.__exit__.assert_called_once_with(None, None, None)
    codex_mock.thread_start.assert_called_once_with(
        cwd=str(tmp_path),
        sandbox=Sandbox.workspace_write,
        model="programmer-model",
        config={
            "model_reasoning_effort": "high",
            "model_reasoning_summary": "auto",
        },
    )
    implementation_prompt = (
        "Implement the following user story: Add a greeting\n\n"
        "Description: As a user, I want a greeting so that I feel welcome.\n\n"
        "Acceptance criteria:\n"
        " - Display a friendly greeting"
    )
    assert [turn_call.args[0][0] for turn_call in thread_mock.turn.call_args_list] == [
        TextInput(text=implementation_prompt),
        TextInput(text=PROGRESS_PROMPT),
    ]

    prepare_branch_mock.assert_called_once_with("greeting")
    commit_story_mock.assert_called_once_with("Add a greeting")
    popen_options = {
        "cwd": tmp_path,
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }
    assert popen_mock.call_args_list == [
        call("lint-project", **popen_options),
        call("typecheck-project", **popen_options),
        call("test-project", **popen_options),
    ]
    assert not list(ralph_dir.glob("*-result.txt"))

    assert programmer.prd.user_stories[0].passes is True
    persisted_prd = json.loads(prd_file.read_text(encoding="utf-8"))
    assert persisted_prd["user_stories"][0]["passes"] is True
