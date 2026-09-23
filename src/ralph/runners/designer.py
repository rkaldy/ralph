from pathlib import Path

from ralph import ui
from ralph.config import RalphConfig
from ralph.exceptions import RalphError
from ralph.runners.runner import CodexRunner


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
        self.task_dir = self.ralph_dir / "tasks"
        self.prds: set[Path] = set()

    def _new_prd_created(self) -> Path | None:
        prds = set(self.task_dir.glob("*.md"))
        new_prds = prds - self.prds
        if len(new_prds) == 1:
            return next(iter(new_prds))
        elif len(new_prds) > 1:
            raise RalphError(f"There are more than one new PRD in {self.task_dir}")
        else:
            return None

    def execute(self) -> None:
        self.prds = set(self.task_dir.glob("*.md"))

        self.session.start_thread()
        self.session.prompt(
            f"Make an interactive user session for creating a PRD for this feature:\n\n{self.feature}",
        )
        while not (prd_file := self._new_prd_created()):
            answer = ui.prompt_user()
            self.session.prompt(answer)

        ui.console.print(f"\nDesign completed. The generated PRD is [bold]{prd_file}[/bold]", style="meta")
        ui.console.print(
            f"Review and update it and then run [bold]ralph converter {prd_file}[/bold]\n", style="meta"
        )
