from pathlib import Path

import pytest

from ralph import config as config_module
from ralph.config import RalphConfig


@pytest.fixture
def user_codex_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    user_config = tmp_path / ".codex" / "config.toml"
    user_config.parent.mkdir()
    user_config.write_text('model = "user-model"\nmodel_reasoning_effort = "user-reasoning"\n')
    monkeypatch.setattr(config_module, "CODEX_CONFIG_PATH", user_config)


def test_model_settings(user_codex_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPT_MODEL_DESIGNER", "env-model")
    monkeypatch.setenv("GPT_REASONING_DESIGNER", "env-reasoning")

    config = RalphConfig()

    assert config.GPT_MODEL_DESIGNER == "env-model"
    assert config.GPT_REASONING_DESIGNER == "env-reasoning"
    assert config.GPT_MODEL_PROGRAMMER == "user-model"
    assert config.GPT_REASONING_PROGRAMMER == "user-reasoning"
