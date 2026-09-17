from pathlib import Path

from pydantic import Field

import ui
from codex import CodexSession
from config import RalphConfig
from exceptions import RalphError
from models import CodexResultBase
from runners.runner import CodexRunner


class ConversionResult(CodexResultBase):
    prd_file: str = Field(
        description="Relative path to the generated JSON PRD, set only after the file has been created."
    )


class Converter(CodexRunner):
    def __init__(self, config: RalphConfig, prd: Path) -> None:
        super().__init__(
            config,
            skill="converter",
            title="Convert PRD to JSON",
            gpt_model=config.GPT_MODEL_DESIGNER,
            reasoning=config.GPT_REASONING_DESIGNER,
        )
        self.prd = prd

    def execute(self, session: CodexSession) -> None:
        output_file = self.ralph_dir / "prd.json"
        output_file.unlink(missing_ok=True)

        session.prompt(f"Convert PRD at {self.prd} to {output_file}.")

        if not output_file.is_file():
            raise RalphError(f"Codex did not complete the conversion to {output_file}")

        ui.console.print(
            f"\nConversion completed. The generated JSON is at [bold]{output_file}[/bold]", style="meta"
        )
        ui.console.print("Now run [bold]ralph programmer[/bold]\n", style="meta")
