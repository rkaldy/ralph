from pathlib import Path

from pydantic import Field

import ui
from config import RalphConfig
from models import CodexResultBase
from runner import CodexRunner
from session import CodexSession
from exceptions import RalphError
from ui import INTRO_BRIGHT


class DesignResult(CodexResultBase):
    prd_file: str = Field(
        description=("Name of the generated PRD. Do not include path. Null if no PRD was generated.")
    )


class Designer(CodexRunner):
    def __init__(self, config: RalphConfig, feature: str) -> None:
        super().__init__(
            config,
            skill="design",
            title="Project Requirement Description designer",
            gpt_model=config.GPT_MODEL_DESIGN,
            reasoning=config.GPT_REASONING_DESIGN,
        )
        self.feature = feature

    def execute(self, session: CodexSession) -> None:
        complete = session.prompt(
            f"Make an interactive user session for creating a PRD for this feature: {self.feature}",
        )
        while not complete:
            answer = ui.prompt_user()
            complete = session.prompt(answer)

        summary = session.summary(DesignResult)
        prd_file = self.ralph_dir / f"tasks/{summary.prd_file}"
        if not prd_file.is_file():
            raise RalphError(f"Codex did not create {prd_file}")

        ui.print_md(f"Design completed. The generated PRD is **{prd_file}** .", INTRO_BRIGHT)
        ui.print_md(f"Review and update it and then run **ralph convert {prd_file}** .\n", INTRO_BRIGHT)
