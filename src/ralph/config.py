import tomllib
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CODEX_CONFIG_PATH = Path.home() / ".codex/config.toml"


class RalphConfig(BaseSettings):
    """Configuration loaded from ``ralph.ini`` in the working directory."""

    model_config = SettingsConfigDict(
        env_file="ralph.ini",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    LINT_COMMAND: str | None = None
    TYPECHECK_COMMAND: str | None = None
    TEST_COMMAND: str | None = None

    SHOW_COMMANDS: bool = False
    MAX_ITERATIONS: int = 5

    GPT_MODEL_DESIGNER: str | None = None
    GPT_REASONING_DESIGNER: str | None = None
    GPT_MODEL_PROGRAMMER: str | None = None
    GPT_REASONING_PROGRAMMER: str | None = None

    @field_validator(
        "GPT_MODEL_DESIGNER",
        "GPT_REASONING_DESIGNER",
        "GPT_MODEL_PROGRAMMER",
        "GPT_REASONING_PROGRAMMER",
        mode="before",
    )
    @classmethod
    def empty_gpt_setting_as_none(cls, value: object) -> object:
        return None if value == "" else value

    @staticmethod
    def _model_settings() -> tuple[str | None, str | None]:
        """Load model settings from the user's Codex configuration."""
        try:
            with CODEX_CONFIG_PATH.open("rb") as config_file:
                config = tomllib.load(config_file)
        except OSError:
            return None, None

        model = config.get("model")
        reasoning = config.get("model_reasoning_effort")
        return (
            model if isinstance(model, str) and model else None,
            reasoning if isinstance(reasoning, str) and reasoning else None,
        )

    @model_validator(mode="after")
    def apply_codex_defaults(self) -> "RalphConfig":
        model, reasoning = self._model_settings()

        if self.GPT_MODEL_DESIGNER is None:
            self.GPT_MODEL_DESIGNER = model
        if self.GPT_REASONING_DESIGNER is None:
            self.GPT_REASONING_DESIGNER = reasoning
        if self.GPT_MODEL_PROGRAMMER is None:
            self.GPT_MODEL_PROGRAMMER = model
        if self.GPT_REASONING_PROGRAMMER is None:
            self.GPT_REASONING_PROGRAMMER = reasoning

        return self
