from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockFixture

from ralph.config import RalphConfig
from ralph.runners.designer import Designer, DesignResult


@pytest.fixture
def session_mock(mocker: MockFixture):
    session_class_mock = mocker.patch("ralph.runners.runner.CodexSession", autospec=True)
    return session_class_mock.return_value


@pytest.fixture
def prompt_user_mock(mocker: MockFixture):
    return mocker.patch("ralph.runners.designer.ui.prompt_user", autospec=True)


@pytest.fixture
def console_mock(mocker: MockFixture):
    return mocker.patch("ralph.runners.designer.ui.console", autospec=True)


@pytest.fixture
def designer(session_mock: MagicMock, tmp_path: Path) -> Designer:
    config = RalphConfig.model_construct(
        GPT_MODEL_DESIGNER="designer-model",
        GPT_REASONING_DESIGNER="high",
    )
    instance = Designer(config, "Add saved searches")
    instance.ralph_dir = tmp_path
    return instance


def test_execute(
    designer: Designer,
    session_mock: MagicMock,
    prompt_user_mock: MagicMock,
    console_mock: MagicMock,
    tmp_path: Path,
) -> None:
    prd_file = tmp_path / "tasks" / "saved-searches.md"
    prd_file.parent.mkdir()
    prd_file.write_text("# PRD: Saved searches\n", encoding="utf-8")
    session_mock.prompt.side_effect = [False, True]
    session_mock.summary.return_value = DesignResult(prd_file="saved-searches.md")
    prompt_user_mock.return_value = "Store search filters"

    designer.execute()

    session_mock.start_thread.assert_called_once_with()
    assert session_mock.prompt.call_args_list == [
        call("Make an interactive user session for creating a PRD for this feature: Add saved searches"),
        call("Store search filters"),
    ]
    prompt_user_mock.assert_called_once_with()
    session_mock.summary.assert_called_once_with(DesignResult)
    assert console_mock.print.call_args_list == [
        call(f"\nDesign completed. The generated PRD is [bold]{prd_file}[/bold]", style="meta"),
        call(
            f"Review and update it and then run [bold]ralph converter {prd_file}[/bold]\n",
            style="meta",
        ),
    ]
