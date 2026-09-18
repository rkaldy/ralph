import os
import subprocess
from pathlib import Path

import pytest

from models import PRD, Story
from runners.programmer import Programmer


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Ralph Test")
    git(tmp_path, "config", "user.email", "ralph@example.test")
    (tmp_path / "README.md").write_text("Initial\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "Initial commit")
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    request.addfinalizer(lambda: os.chdir(original_cwd))
    return tmp_path


def programmer(branch_name: str = "ralph/feature") -> Programmer:
    instance = Programmer.__new__(Programmer)
    instance.prd = PRD(name="Feature", branch_name=branch_name, user_stories=[])
    return instance


def story(title: str = "Implement feature") -> Story:
    return Story(
        id="US-001",
        title=title,
        description="Description",
        priority=1,
        acceptance_criteria=[],
        passes=False,
    )


def test_prepare_branch_creates_and_switches_to_prd_branch(repository: Path) -> None:
    instance = programmer()

    instance.prepare_branch()

    assert git(repository, "branch", "--show-current") == "ralph/feature"


def test_prepare_branch_switches_to_existing_prd_branch(repository: Path) -> None:
    instance = programmer()
    git(repository, "branch", "ralph/feature")

    instance.prepare_branch()

    assert git(repository, "branch", "--show-current") == "ralph/feature"


def test_commit_story_commits_all_changes_with_story_title(repository: Path) -> None:
    instance = programmer()
    changed_file = repository / "README.md"
    changed_file.write_text("Changed\n", encoding="utf-8")
    (repository / "new-file.txt").write_text("New\n", encoding="utf-8")

    instance.commit_story(story())

    assert git(repository, "log", "-1", "--format=%s") == "Implement feature"
    assert git(repository, "status", "--porcelain") == ""
