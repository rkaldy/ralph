from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

import runners.runner as runner_module
import ui
from config import RalphConfig
from exceptions import RalphError
from runners.designer import Designer, DesignResult


@pytest.fixture
def mocked_designer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    monkeypatch.chdir(tmp_path)
    session = MagicMock(name="session")
    session_factory = MagicMock(name="CodexSession", return_value=session)
    prompt_user = MagicMock(name="prompt_user")
    console = MagicMock(name="console")
    monkeypatch.setattr(runner_module, "CodexSession", session_factory)
    monkeypatch.setattr(ui, "prompt_user", prompt_user)
    monkeypatch.setattr(ui, "console", console)
    return session_factory, session, prompt_user, console


def make_config() -> RalphConfig:
    return RalphConfig.model_construct(
        GPT_MODEL_DESIGNER="designer-model",
        GPT_REASONING_DESIGNER="high",
    )


def test_design_result_identifies_generated_prd_file() -> None:
    result = DesignResult.model_validate({"prd_file": "feature.md"})

    assert result.prd_file == "feature.md"


def test_designer_uses_configured_session_and_retains_feature(
    mocked_designer: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    session_factory, session, _, _ = mocked_designer
    config = make_config()

    designer = Designer(config, "Add saved searches")

    session_factory.assert_called_once_with(
        config,
        "designer",
        "designer-model",
        "high",
    )
    assert designer.session is session
    assert designer.feature == "Add saved searches"


def test_execute_collects_answers_and_reports_generated_prd(
    mocked_designer: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    tmp_path: Path,
) -> None:
    _, session, prompt_user, console = mocked_designer
    designer = Designer(make_config(), "Add saved searches")
    prd_file = tmp_path / ".ralph/tasks/saved-searches.md"
    prd_file.parent.mkdir()
    prd_file.write_text("# PRD: Saved searches\n", encoding="utf-8")
    session.prompt.side_effect = [False, False, True]
    prompt_user.side_effect = ["Store search filters", "Share them with a team"]
    session.summary.return_value = DesignResult(prd_file="saved-searches.md")

    designer.execute()

    session.start_thread.assert_called_once_with()
    assert session.prompt.call_args_list == [
        call("Make an interactive user session for creating a PRD for this feature: Add saved searches"),
        call("Store search filters"),
        call("Share them with a team"),
    ]
    assert prompt_user.call_count == 2
    session.summary.assert_called_once_with(DesignResult)
    assert console.print.call_args_list == [
        call(
            "\nDesign completed. The generated PRD is [bold].ralph/tasks/saved-searches.md[/bold]",
            style="meta",
        ),
        call(
            "Review and update it and then run [bold]ralph converter .ralph/tasks/saved-searches.md[/bold]\n",
            style="meta",
        ),
    ]


def test_execute_raises_when_summary_prd_does_not_exist(
    mocked_designer: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    _, session, prompt_user, console = mocked_designer
    designer = Designer(make_config(), "Add saved searches")
    session.prompt.return_value = True
    session.summary.return_value = DesignResult(prd_file="missing.md")

    with pytest.raises(RalphError, match=r"Codex did not create \.ralph/tasks/missing\.md"):
        designer.execute()

    session.start_thread.assert_called_once_with()
    session.summary.assert_called_once_with(DesignResult)
    prompt_user.assert_not_called()
    console.print.assert_not_called()
