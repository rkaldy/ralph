import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from ralph.config import RalphConfig
from ralph.runners.programmer import PROGRESS_PROMPT, Programmer
from tests.integration.conftest import assert_live_mock_writes, codex_session_mock


class QAProcess:
    def __init__(self, output: str, return_code: int) -> None:
        self.stdout = iter([output])
        self.return_code = return_code

    def __enter__(self) -> "QAProcess":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def wait(self) -> int:
        return self.return_code


@pytest.fixture
def prd_json(tmp_path: Path) -> Path:
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
    return prd_file


IMPLEMENTATION_PROMPT = """Implement the following user story: Add a greeting

Description: As a user, I want a greeting so that I feel welcome.

Acceptance criteria:
 - Display a friendly greeting"""

ERROR_FIXING_PROMPT = """Fix errors in the implementation of the user story: Add a greeting

The test checker found errors, its output is stored in the file `.ralph/test-result.txt`.

Acceptance criteria:
 - Display a friendly greeting"""


def programmer_codex_behavior(prompt: str) -> str:
    if prompt == IMPLEMENTATION_PROMPT:
        return "Implementing the story"
    elif prompt == ERROR_FIXING_PROMPT:
        return "Fixing errors"
    elif prompt == PROGRESS_PROMPT:
        return "Updating progress file"
    else:
        raise AssertionError(f"Unexpected prompt: {prompt}")


def test_programmer_happy_path(
    mocker: MockerFixture,
    monkeypatch,
    tmp_path: Path,
    prd_json: Path,
    live_mock,
    console_mock,
):
    monkeypatch.chdir(tmp_path)
    prepare_branch_mock = mocker.patch("ralph.runners.programmer.prepare_branch", autospec=True)
    commit_story_mock = mocker.patch("ralph.runners.programmer.commit_story", autospec=True)
    mocker.patch(
        "ralph.runners.programmer.subprocess.Popen",
        side_effect=[
            QAProcess("Lint passed", 0),
            QAProcess("One test failed", 1),
            QAProcess("Lint passed", 0),
            QAProcess("Tests passed", 0),
        ],
    )
    codex_session_mock(mocker, programmer_codex_behavior)
    config = RalphConfig.model_construct(
        LINT_COMMAND="make lint",
        TYPECHECK_COMMAND=None,
        TEST_COMMAND="make test",
        MAX_ITERATIONS=3,
    )

    Programmer(config).run()

    prepare_branch_mock.assert_called_once_with("greeting")
    commit_story_mock.assert_called_once_with("Add a greeting")
    assert live_mock.update.call_count == 3
    assert_live_mock_writes(live_mock, ["Implementing the story", "Fixing errors", "Updating progress file"])

    assert not list((tmp_path / ".ralph").glob("*-result.txt"))

    persisted_prd = json.loads(prd_json.read_text(encoding="utf-8"))
    assert persisted_prd["user_stories"][0]["passes"] is True
