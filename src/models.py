import pydantic
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class BaseModel(pydantic.BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
    )


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
    description: str
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
