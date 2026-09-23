import pytest

from ralph.models import PRD, Story


def story(*, story_id: str, priority: int, passes: bool) -> Story:
    return Story(
        id=story_id,
        title=f"Story {story_id}",
        description="Description",
        priority=priority,
        acceptance_criteria=[],
        passes=passes,
    )


def prd(*stories: Story) -> PRD:
    return PRD(name="Feature", branch_name="ralph/feature", user_stories=list(stories))


def test_next_story_returns_lowest_priority_number_that_has_not_passed() -> None:
    higher_priority_number = story(story_id="US-003", priority=3, passes=False)
    passed = story(story_id="US-001", priority=1, passes=True)
    expected = story(story_id="US-002", priority=2, passes=False)

    assert prd(higher_priority_number, passed, expected).next_story() is expected


def test_next_story_returns_none_when_all_stories_have_passed() -> None:
    product = prd(
        story(story_id="US-001", priority=1, passes=True),
        story(story_id="US-002", priority=2, passes=True),
    )

    assert product.next_story() is None


@pytest.mark.parametrize(
    ("stories", "expected_count"),
    [
        ([], 0),
        (
            [
                story(story_id="US-001", priority=1, passes=True),
                story(story_id="US-002", priority=2, passes=False),
                story(story_id="US-003", priority=3, passes=True),
            ],
            2,
        ),
        (
            [
                story(story_id="US-001", priority=1, passes=True),
                story(story_id="US-002", priority=2, passes=True),
            ],
            2,
        ),
    ],
    ids=["empty", "partially-complete", "fully-complete"],
)
def test_num_passed_stories(stories: list[Story], expected_count: int) -> None:
    assert prd(*stories).num_passed_stories() == expected_count
