import ui
from config import RalphConfig
from runner import CodexRunner
from session import CodexSession
from ui import INTRO_BRIGHT


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
        response = session.prompt(
            f"Make an interactive user session for creating a PRD for this feature: {self.feature}"
        )
        while True:
            if response.completed:
                ui.print_md(f"Design completed. The generated PRD is **{response.file}** .", INTRO_BRIGHT)
                ui.print_md(
                    f"Review and update it and then run **ralph convert {response.file}** .\n", INTRO_BRIGHT
                )
                return

            answer = ui.prompt_user()
            response = session.prompt(answer)
