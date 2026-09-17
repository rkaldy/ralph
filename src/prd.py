from models import BaseModel, Story


class PRD(BaseModel):
    branch_name: str
    original_prd: str
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
