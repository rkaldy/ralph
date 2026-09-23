from pathlib import Path

from pytest_mock import MockerFixture

from ralph.config import RalphConfig
from ralph.runners.designer import Designer
from tests.integration.conftest import assert_live_mock_writes, codex_session_mock


def test_designer_happy_path(mocker: MockerFixture, monkeypatch, tmp_path: Path, live_mock, console_mock):
    prd_file = tmp_path / ".ralph" / "tasks" / "saved-searches.md"

    def designer_codex_behavior(prompt: str) -> str | None:
        if (
            prompt
            == "Make an interactive user session for creating a PRD for this feature:\n\nAdd saved searches"
        ):
            return "Where should I keep them?"
        elif prompt == "In the database":
            prd_file.parent.mkdir(parents=True)
            prd_file.write_text("# PRD: Saved searches", encoding="utf-8")
            return f"PRD stored to {prd_file.name}"
        raise AssertionError(f"Unexpected prompt: {prompt}")

    monkeypatch.chdir(tmp_path)
    prompt_user_mock = mocker.patch("ralph.ui.prompt_user", autospec=True, return_value="In the database")
    codex_session_mock(mocker, designer_codex_behavior)
    config = RalphConfig.model_construct(
        GPT_MODEL_DESIGNER="designer-model",
        GPT_REASONING_DESIGNER="high",
    )

    Designer(config, "Add saved searches").run()

    prompt_user_mock.assert_called_once()
    assert live_mock.update.call_count == 2
    assert_live_mock_writes(live_mock, ["Where should I keep them?", f"PRD stored to {prd_file.name}"])
    assert prd_file.is_file()
