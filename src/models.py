import pydantic
from pydantic import ConfigDict, BaseModel
from pydantic.alias_generators import to_camel


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

    def set_passed(self, story_id: str) -> None:
        for story in self.user_stories:
            if story.id == story_id:
                story.passes = True
                return
