from pathlib import Path

import pytest

import config as config_module
from config import RalphConfig


@pytest.fixture
def codex_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Keep every settings source independent of the developer's machine."""
    monkeypatch.chdir(tmp_path)
    for field_name in RalphConfig.model_fields:
        monkeypatch.delenv(field_name, raising=False)

    path = tmp_path / ".codex" / "config.toml"
    monkeypatch.setattr(config_module, "CODEX_CONFIG_PATH", path)
    return path


def write_codex_config(path: Path, *, model: str, reasoning: str) -> None:
    path.parent.mkdir()
    path.write_text(
        f'model = "{model}"\nmodel_reasoning_effort = "{reasoning}"\n',
        encoding="utf-8",
    )


def test_defaults_are_used_without_environment_or_config_file(codex_config_path: Path) -> None:
    config = RalphConfig()

    assert config.LINT_COMMAND is None
    assert config.TYPECHECK_COMMAND is None
    assert config.TEST_COMMAND is None
    assert config.SHOW_COMMANDS is False
    assert config.MAX_ITERATIONS == 5
    assert config.GPT_MODEL_DESIGNER is None
    assert config.GPT_REASONING_DESIGNER is None
    assert config.GPT_MODEL_PROGRAMMER is None
    assert config.GPT_REASONING_PROGRAMMER is None


def test_empty_ralph_model_settings_are_normalized_before_codex_defaults(
    codex_config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_codex_config(codex_config_path, model="codex-model", reasoning="high")
    for field_name in (
        "GPT_MODEL_DESIGNER",
        "GPT_REASONING_DESIGNER",
        "GPT_MODEL_PROGRAMMER",
        "GPT_REASONING_PROGRAMMER",
    ):
        monkeypatch.setenv(field_name, "")

    config = RalphConfig()

    assert config.GPT_MODEL_DESIGNER == "codex-model"
    assert config.GPT_REASONING_DESIGNER == "high"
    assert config.GPT_MODEL_PROGRAMMER == "codex-model"
    assert config.GPT_REASONING_PROGRAMMER == "high"


def test_codex_model_settings_supply_missing_ralph_values(codex_config_path: Path) -> None:
    write_codex_config(codex_config_path, model="codex-model", reasoning="medium")

    config = RalphConfig()

    assert config.GPT_MODEL_DESIGNER == "codex-model"
    assert config.GPT_REASONING_DESIGNER == "medium"
    assert config.GPT_MODEL_PROGRAMMER == "codex-model"
    assert config.GPT_REASONING_PROGRAMMER == "medium"


def test_ralph_model_settings_take_precedence_over_codex_defaults(
    codex_config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_codex_config(codex_config_path, model="codex-model", reasoning="medium")
    ralph_settings = {
        "GPT_MODEL_DESIGNER": "designer-model",
        "GPT_REASONING_DESIGNER": "high",
        "GPT_MODEL_PROGRAMMER": "programmer-model",
        "GPT_REASONING_PROGRAMMER": "low",
    }
    for field_name, value in ralph_settings.items():
        monkeypatch.setenv(field_name, value)

    config = RalphConfig()

    assert config.GPT_MODEL_DESIGNER == "designer-model"
    assert config.GPT_REASONING_DESIGNER == "high"
    assert config.GPT_MODEL_PROGRAMMER == "programmer-model"
    assert config.GPT_REASONING_PROGRAMMER == "low"
