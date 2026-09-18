import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai_codex import SkillInput, TextInput, Thread
from pytest_mock import MockerFixture, MockFixture

import codex
from codex import CodexSession
from config import RalphConfig
from exceptions import RalphError


@pytest.fixture
def thread_mock():
    return MagicMock(spec=Thread)


@pytest.fixture
def codex_mock(mocker: MockFixture, thread_mock):
    codex_class_mock = mocker.patch("codex.Codex", autospec=True)
    codex_mock = codex_class_mock.return_value
    codex_mock.thread_start.return_value = thread_mock
    return codex_mock


@pytest.fixture
def session(codex_mock) -> CodexSession:
    return CodexSession(config=RalphConfig(), skill="test-skill")


def create_skill(path: Path) -> Path:
    path.parent.mkdir(parents=True)
    path.write_text("# Test skill\n", encoding="utf-8")
    return path.resolve()


@pytest.fixture
def skills(mocker: MockerFixture, tmp_path: Path) -> tuple[Path, Path]:
    local_root = tmp_path / "local"
    installed_prefix = tmp_path / "prefix"
    local_skill = create_skill(local_root / "skills/test-skill/SKILL.md")
    installed_skill = create_skill(installed_prefix / "share/ralph/skills/test-skill/SKILL.md")
    mocker.patch.object(codex, "__file__", str(local_root / "src/codex.py"))
    mocker.patch.object(sys, "prefix", str(installed_prefix))
    return local_skill, installed_skill


def test_prompt_uses_local_skill(
    session: CodexSession,
    thread_mock: MagicMock,
    skills: tuple[Path, Path],
):
    local_skill, _ = skills

    session.start_thread()
    session.prompt("Implement the story")

    thread_mock.turn.assert_called_once_with(
        [
            TextInput(text="Implement the story"),
            SkillInput(name="test-skill", path=str(local_skill)),
        ]
    )


def test_prompt_thread_not_started(session: CodexSession):
    with pytest.raises(RalphError, match="Codex thread not started"):
        session.prompt("Implement the story")


def test_prompt_uses_installed_skill(
    session: CodexSession,
    thread_mock,
    skills: tuple[Path, Path],
):
    local_skill, installed_skill = skills
    local_skill.unlink()

    session.start_thread()
    session.prompt("Implement the story")

    thread_mock.turn.assert_called_once_with(
        [
            TextInput(text="Implement the story"),
            SkillInput(name="test-skill", path=str(installed_skill)),
        ]
    )


def test_prompt_skill_not_found(
    session: CodexSession,
    thread_mock,
    skills: tuple[Path, Path],
):
    local_skill, installed_skill = skills
    local_skill.unlink()
    installed_skill.unlink()

    session.start_thread()
    with pytest.raises(RalphError, match="'test-skill' skill is not installed"):
        session.prompt("Implement the story")

    thread_mock.turn.assert_not_called()
