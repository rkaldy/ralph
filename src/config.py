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

    GPT_MODEL_DESIGN: str | None = None
    GPT_REASONING_DESIGN: str | None = None
    GPT_MODEL_IMPLEMENT: str | None = None
    GPT_REASONING_IMPLEMENT: str | None = None

    @field_validator(
        "GPT_MODEL_DESIGN",
        "GPT_REASONING_DESIGN",
        "GPT_MODEL_IMPLEMENT",
        "GPT_REASONING_IMPLEMENT",
        mode="before",
    )
    @classmethod
    def empty_gpt_setting_as_none(cls, value: object) -> object:
        return None if value == "" else value

    def _model_settings(self) -> tuple[str | None, str | None]:
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

        if self.GPT_MODEL_DESIGN is None:
            self.GPT_MODEL_DESIGN = model
        if self.GPT_REASONING_DESIGN is None:
            self.GPT_REASONING_DESIGN = reasoning
        if self.GPT_MODEL_IMPLEMENT is None:
            self.GPT_MODEL_IMPLEMENT = model
        if self.GPT_REASONING_IMPLEMENT is None:
            self.GPT_REASONING_IMPLEMENT = reasoning

        return self
