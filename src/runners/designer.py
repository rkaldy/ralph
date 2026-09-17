from pydantic import Field

import ui
from config import RalphConfig
from exceptions import RalphError
from models import CodexResultBase
from runners.runner import CodexRunner


class DesignResult(CodexResultBase):
    prd_file: str = Field(
        description=("Name of the generated PRD. Do not include path. Null if no PRD was generated.")
    )


class Designer(CodexRunner):
    def __init__(self, config: RalphConfig, feature: str) -> None:
        super().__init__(
            config,
            skill="designer",
            title="Project Requirement Description designer",
            gpt_model=config.GPT_MODEL_DESIGNER,
            reasoning=config.GPT_REASONING_DESIGNER,
        )
        self.feature = feature

    def execute(self) -> None:
        self.session.start_thread()
        complete = self.session.prompt(
            f"Make an interactive user session for creating a PRD for this feature: {self.feature}",
        )
        while not complete:
            answer = ui.prompt_user()
            complete = self.session.prompt(answer)

        summary = self.session.summary(DesignResult)
        prd_file = self.ralph_dir / f"tasks/{summary.prd_file}"
        if not prd_file.is_file():
            raise RalphError(f"Codex did not create {prd_file}")

        ui.console.print(f"\nDesign completed. The generated PRD is [bold]{prd_file}[/bold]", style="meta")
        ui.console.print(
            f"Review and update it and then run [bold]ralph converter {prd_file}[/bold]\n", style="meta"
        )
