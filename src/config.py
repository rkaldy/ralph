import typer
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from codex import CodexSession
from ralph import app


class RalphConfig(BaseSettings):
    """Configuration loaded from ``ralph.ini`` in the working directory."""

    model_config = SettingsConfigDict(
        env_file="ralph.ini",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    LINT_COMMAND: str
    TYPECHECK_COMMAND: str
    TEST_COMMAND: str
    GPT_MODEL_DESIGN: str | None = None
    GPT_REASONING_DESIGN: str | None = None
    GPT_MODEL_EXECUTION: str | None = None
    GPT_REASONING_EXECUTION: str | None = None

    @field_validator(
        "GPT_MODEL_DESIGN",
        "GPT_REASONING_DESIGN",
        "GPT_MODEL_EXECUTION",
        "GPT_REASONING_EXECUTION",
        mode="before",
    )
    @classmethod
    def empty_gpt_setting_as_none(cls, value: object) -> object:
        """Treat an empty INI value as an unset GPT option."""
        return None if value == "" else value

    @model_validator(mode="after")
    def apply_codex_defaults(self) -> "RalphConfig":
        """Use the system Codex model settings for unset GPT options."""
        model, reasoning = CodexSession.model_settings()

        if self.GPT_MODEL_DESIGN is None:
            self.GPT_MODEL_DESIGN = model
        if self.GPT_REASONING_DESIGN is None:
            self.GPT_REASONING_DESIGN = reasoning
        if self.GPT_MODEL_EXECUTION is None:
            self.GPT_MODEL_EXECUTION = model
        if self.GPT_REASONING_EXECUTION is None:
            self.GPT_REASONING_EXECUTION = reasoning

        return self


@app.callback()
def load_config(ctx: typer.Context) -> None:
    ctx.obj = RalphConfig()
