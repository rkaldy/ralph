from pydantic import BaseModel, ConfigDict


class CodexResultBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Story(BaseModel):
    id: str
    title: str
    description: str
    priority: int
    acceptance_criteria: list[str]
    passes: bool


class PRD(BaseModel):
    name: str
    branch_name: str
    user_stories: list[Story]

    def next_story(self) -> Story | None:
        return min(
            (story for story in self.user_stories if not story.passes),
            key=lambda story: story.priority,
            default=None,
        )

    def num_passed_stories(self) -> int:
        return sum(1 for story in self.user_stories if story.passes)
