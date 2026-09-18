import re
from pathlib import Path

from pydantic import Field

import ui
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

    PRD_CHAPTER = re.compile(r"^#{2} (.*)$")

    def create_progress_file(self) -> None:
        prd_text = self.prd.read_text(encoding="utf-8")
        inside_user_stories = False
        with open(self.ralph_dir / "progress.md", "w") as progress_file:
            for line in prd_text.splitlines():
                if (chapter := self.PRD_CHAPTER.match(line)) is not None:
                    inside_user_stories = chapter.group(1) == "User Stories"
                if not inside_user_stories:
                    progress_file.write(f"{line}\n")

        ui.console.print(f"Progress initialized at [bold]{progress_file.name}[/bold]", style="meta")

    def create_prd_json(self) -> None:
        output_file = self.ralph_dir / "prd.json"
        output_file.unlink(missing_ok=True)

        self.session.start_thread()
        self.session.prompt(f"Convert PRD at {self.prd} to {output_file}.")

        if not output_file.is_file():
            raise RalphError(f"Codex did not complete the conversion to {output_file}")
        ui.console.print(
            f"\nConversion completed. The generated JSON is at [bold]{output_file}[/bold]", style="meta"
        )

    def execute(self) -> None:
        # self.create_prd_json()
        self.create_progress_file()
        ui.console.print("Now run [bold]ralph programmer[/bold]\n", style="meta")
