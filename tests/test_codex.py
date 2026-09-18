import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai_codex import Sandbox

import codex
from config import RalphConfig
from exceptions import RalphError


@pytest.fixture
def codex_mocks(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    factory = MagicMock(name="Codex")
    client = MagicMock(name="codex_client")
    factory.return_value = client
    monkeypatch.setattr(codex, "Codex", factory)
    return factory, client


def make_session(
    codex_mocks: tuple[MagicMock, MagicMock],
    *,
    skill: str = "test-skill",
    model: str | None = None,
    reasoning: str | None = None,
) -> codex.CodexSession:
    factory, _ = codex_mocks
    config = RalphConfig.model_construct(SHOW_COMMANDS=False)
    session = codex.CodexSession(config, skill, model, reasoning)
    factory.assert_called_once_with()
    return session


def test_context_manager_enters_and_exits_codex(codex_mocks: tuple[MagicMock, MagicMock]) -> None:
    _, client = codex_mocks
    session = make_session(codex_mocks)

    with session as entered_session:
        assert entered_session is session

    client.__enter__.assert_called_once_with()
    client.__exit__.assert_called_once_with(None, None, None)


def test_skill_path_prefers_checkout_skill(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_skill = checkout_root / "skills/test-skill/SKILL.md"
    checkout_skill.parent.mkdir(parents=True)
    checkout_skill.write_text("checkout", encoding="utf-8")
    installed_prefix = tmp_path / "prefix"
    installed_skill = installed_prefix / "share/ralph/skills/test-skill/SKILL.md"
    installed_skill.parent.mkdir(parents=True)
    installed_skill.write_text("installed", encoding="utf-8")
    monkeypatch.setattr(codex, "__file__", str(checkout_root / "src/codex.py"))
    monkeypatch.setattr(sys, "prefix", str(installed_prefix))
    session = make_session(codex_mocks)

    assert session._skill_path() == checkout_skill.resolve()


def test_skill_path_falls_back_to_installed_skill(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout_root = tmp_path / "checkout"
    installed_prefix = tmp_path / "prefix"
    installed_skill = installed_prefix / "share/ralph/skills/test-skill/SKILL.md"
    installed_skill.parent.mkdir(parents=True)
    installed_skill.write_text("installed", encoding="utf-8")
    monkeypatch.setattr(codex, "__file__", str(checkout_root / "src/codex.py"))
    monkeypatch.setattr(sys, "prefix", str(installed_prefix))
    session = make_session(codex_mocks)

    assert session._skill_path() == installed_skill.resolve()


def test_skill_path_raises_when_skill_is_not_installed(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(codex, "__file__", str(tmp_path / "checkout/src/codex.py"))
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "prefix"))
    session = make_session(codex_mocks, skill="missing")

    with pytest.raises(RalphError, match="'missing' skill is not installed"):
        session._skill_path()


@pytest.mark.parametrize(
    ("reasoning", "expected_config"),
    [
        ("high", {"model_reasoning_effort": "high", "model_reasoning_summary": "auto"}),
        (None, {"model_reasoning_summary": "auto"}),
    ],
)
def test_start_thread_stores_thread_and_supplies_configuration(
    codex_mocks: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reasoning: str | None,
    expected_config: dict[str, str],
) -> None:
    _, client = codex_mocks
    monkeypatch.chdir(tmp_path)
    session = make_session(codex_mocks, model="test-model", reasoning=reasoning)
    thread = MagicMock(name="thread")
    client.thread_start.return_value = thread

    session.start_thread()

    assert session.thread is thread
    client.thread_start.assert_called_once_with(
        cwd=str(tmp_path),
        sandbox=Sandbox.workspace_write,
        model="test-model",
        config=expected_config,
    )
