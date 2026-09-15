from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from session import CodexSession


class RalphConfig(BaseSettings):
    """Configuration loaded from ``ralph.ini`` in the working directory."""

    model_config = SettingsConfigDict(
        env_file="ralph.ini",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    LINT_COMMAND: str = ""
    TYPECHECK_COMMAND: str = ""
    TEST_COMMAND: str = ""

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

    @model_validator(mode="after")
    def apply_codex_defaults(self) -> "RalphConfig":
        model, reasoning = CodexSession.model_settings()

        if self.GPT_MODEL_DESIGN is None:
            self.GPT_MODEL_DESIGN = model
        if self.GPT_REASONING_DESIGN is None:
            self.GPT_REASONING_DESIGN = reasoning
        if self.GPT_MODEL_IMPLEMENT is None:
            self.GPT_MODEL_IMPLEMENT = model
        if self.GPT_REASONING_IMPLEMENT is None:
            self.GPT_REASONING_IMPLEMENT = reasoning

        return self
