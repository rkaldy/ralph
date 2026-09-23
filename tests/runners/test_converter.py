import json
import re
from pathlib import Path

import pytest

from ralph.config import RalphConfig
from ralph.runners.converter import Converter, MarkdownChapter


@pytest.fixture
def prd_markdown() -> str:
    return """# PRD: Task Priority System

## Introduction

Help users focus on the tasks that matter most.

## Goals

- Make priorities visible.
- Allow users to change priorities.

## User Stories

### US-001: Store task priorities
**Description:** As a developer, I want task priorities persisted between sessions.

**Acceptance Criteria:**
- [ ] Add a priority field with a medium default
- [ ] Persist priority changes

### US-002: Display task priorities
**Description:** As a user, I want to see each task's priority at a glance.

**Acceptance Criteria:**
- [ ] Show a priority badge on every task
- [ ] Use distinct colors for each priority
    """


def converter_factory(tmp_path: Path, prd_markdown: str) -> Converter:
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(prd_markdown)
    converter = Converter(RalphConfig(), prd_file)
    converter.ralph_dir = tmp_path
    return converter


def test_parse_markdown(tmp_path: Path):
    converter = converter_factory(
        tmp_path,
        """# PRD: Nested Feature
Overview text.
## Parent
Parent text.
### Child
Child text.
#### Grandchild
Grandchild text.
## Sibling
Sibling text.
""",
    )
    converter.parse_markdown()

    assert converter.prd_markdown == MarkdownChapter(
        chapters={
            "PRD: Nested Feature": MarkdownChapter(
                text=["Overview text.\n"],
                chapters={
                    "Parent": MarkdownChapter(
                        text=["Parent text.\n"],
                        chapters={
                            "Child": MarkdownChapter(
                                text=["Child text.\n"],
                                chapters={
                                    "Grandchild": MarkdownChapter(text=["Grandchild text.\n"]),
                                },
                            ),
                        },
                    ),
                    "Sibling": MarkdownChapter(text=["Sibling text.\n"]),
                },
            ),
        }
    )


def test_parse_markdown_rejects_duplicate_headings_at_same_level(tmp_path: Path) -> None:
    converter = converter_factory(
        tmp_path,
        """# PRD: Duplicate Feature
## User Stories
### US-001: Repeated story
First body.
### US-001: Repeated story
Second body.
""",
    )

    with pytest.raises(
        ValueError,
        match=re.escape("Duplicate Markdown heading 'US-001: Repeated story'"),
    ):
        converter.parse_markdown()


def test_create_prd_json(tmp_path: Path, prd_markdown: str):
    converter = converter_factory(tmp_path, prd_markdown)
    converter.parse_markdown()
    converter.create_prd_json()

    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    assert prd == {
        "name": "Task Priority System",
        "branch_name": "task-priority-system",
        "user_stories": [
            {
                "id": "US-001",
                "title": "Store task priorities",
                "description": "As a developer, I want task priorities persisted between sessions.",
                "priority": 1,
                "acceptance_criteria": [
                    "Add a priority field with a medium default",
                    "Persist priority changes",
                ],
                "passes": False,
            },
            {
                "id": "US-002",
                "title": "Display task priorities",
                "description": "As a user, I want to see each task's priority at a glance.",
                "priority": 2,
                "acceptance_criteria": [
                    "Show a priority badge on every task",
                    "Use distinct colors for each priority",
                ],
                "passes": False,
            },
        ],
    }


def test_create_progress_file(tmp_path: Path, prd_markdown: str):
    converter = converter_factory(tmp_path, prd_markdown)
    converter.parse_markdown()
    converter.create_progress_file()

    progress = (tmp_path / "progress.md").read_text(encoding="utf-8")
    assert (
        progress
        == """# PRD: Task Priority System

## Introduction

Help users focus on the tasks that matter most.

## Goals

- Make priorities visible.
- Allow users to change priorities.

## User Stories

- **US-001: Store task priorities** - As a developer, I want task priorities persisted between sessions.
- **US-002: Display task priorities** - As a user, I want to see each task's priority at a glance.


## Codebase Patterns

## Gotchas Encountered
"""
    )
