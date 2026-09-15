from pathlib import Path

import ui
from config import RalphConfig
from runner import CodexRunner
from session import CodexSession, RalphError
from ui import INTRO_BRIGHT


class Converter(CodexRunner):
    def __init__(self, config: RalphConfig, prd: Path) -> None:
        super().__init__(
            config,
            skill="convert",
            title="Convert PRD to JSON",
            gpt_model=config.GPT_MODEL_DESIGN,
            reasoning=config.GPT_REASONING_DESIGN,
        )
        self.prd = prd

    def execute(self, session: CodexSession) -> None:
        output_file = self.ralph_dir / "prd.json"
        output_file.unlink(missing_ok=True)
        response = session.prompt(f"Convert PRD at {self.prd} to {output_file}.")

        if not response.file or response.file.resolve() != output_file.resolve():
            raise RalphError(f"Codex did not complete the conversion to {output_file}")

        ui.print_md(f"Conversion completed. The generated JSON is at **{output_file}** .", INTRO_BRIGHT)
        ui.print_md("Now run **ralph implement** .\n", INTRO_BRIGHT)
