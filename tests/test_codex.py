from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai_codex import SkillInput, TextInput, Thread
from pytest_mock import MockerFixture, MockFixture

from ralph import codex
from ralph.codex import CodexSession
from ralph.config import RalphConfig
from ralph.exceptions import RalphError


@pytest.fixture
def thread_mock():
    return MagicMock(spec=Thread)


@pytest.fixture
def codex_mock(mocker: MockFixture, thread_mock):
    codex_class_mock = mocker.patch("ralph.codex.Codex", autospec=True)
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
def skill(mocker: MockerFixture, tmp_path: Path) -> Path:
    package_root = tmp_path / "ralph"
    skill = create_skill(package_root / "skills/test-skill/SKILL.md")
    mocker.patch.object(codex, "__file__", str(package_root / "codex.py"))
    return skill


def test_prompt_uses_packaged_skill(
    session: CodexSession,
    thread_mock: MagicMock,
    skill: Path,
):
    session.start_thread()
    session.prompt("Implement the story")

    thread_mock.turn.assert_called_once_with(
        [
            TextInput(text="Implement the story"),
            SkillInput(name="test-skill", path=str(skill)),
        ]
    )


def test_prompt_thread_not_started(session: CodexSession):
    with pytest.raises(RalphError, match="Codex thread not started"):
        session.prompt("Implement the story")


def test_prompt_skill_not_found(
    session: CodexSession,
    thread_mock,
    skill: Path,
):
    skill.unlink()

    session.start_thread()
    with pytest.raises(RalphError, match="'test-skill' skill is not installed"):
        session.prompt("Implement the story")

    thread_mock.turn.assert_not_called()
