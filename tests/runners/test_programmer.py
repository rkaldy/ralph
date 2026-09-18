import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

import runners.runner as runner_module
import ui
from config import RalphConfig
from models import Story
from runners.programmer import QA, Programmer


def make_config() -> RalphConfig:
    return RalphConfig.model_construct(
        GPT_MODEL_PROGRAMMER="programmer-model",
        GPT_REASONING_PROGRAMMER="high",
        LINT_COMMAND="ruff check .",
        TYPECHECK_COMMAND="mypy .",
        TEST_COMMAND="pytest",
        MAX_ITERATIONS=7,
    )


@pytest.fixture
def programmer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Programmer, MagicMock, MagicMock]:
    monkeypatch.chdir(tmp_path)
    session = MagicMock(name="session")
    session_factory = MagicMock(name="CodexSession", return_value=session)
    monkeypatch.setattr(runner_module, "CodexSession", session_factory)
    monkeypatch.setattr(ui, "console", MagicMock(name="console"))
    return Programmer(make_config()), session_factory, session


@pytest.fixture
def story() -> Story:
    return Story(
        id="US-007",
        title="Quality-check helpers",
        description="Persist failed checks so retries have useful context.",
        priority=1,
        acceptance_criteria=[
            "Run every configured quality check",
            "Include failed check output in retry context",
        ],
        passes=False,
    )


def mock_process(lines: list[str] | None, return_code: int = 0) -> MagicMock:
    process = MagicMock(name="process")
    process.stdout = None if lines is None else iter(lines)
    process.wait.return_value = return_code
    process.__enter__.return_value = process
    process.__exit__.return_value = False
    return process


def test_construction_maps_quality_commands_and_max_iterations(
    programmer: tuple[Programmer, MagicMock, MagicMock],
) -> None:
    instance, session_factory, session = programmer
    config = make_config()

    session_factory.assert_called_once_with(
        config,
        "programmer",
        "programmer-model",
        "high",
    )
    assert instance.session is session
    assert instance.max_iterations == 7
    assert instance.qa_commands == {
        QA.LINT: "ruff check .",
        QA.TYPECHECK: "mypy .",
        QA.TEST: "pytest",
    }


def test_delete_qa_results_removes_known_files_and_tolerates_missing_files(
    programmer: tuple[Programmer, MagicMock, MagicMock],
) -> None:
    instance, _, _ = programmer
    lint_result = instance.ralph_dir / "lint-result.txt"
    test_result = instance.ralph_dir / "test-result.txt"
    lint_result.write_text("lint failed", encoding="utf-8")
    test_result.write_text("tests failed", encoding="utf-8")

    instance.delete_qa_results()
    instance.delete_qa_results()

    assert all(not (instance.ralph_dir / f"{qa.value}-result.txt").exists() for qa in QA)


@pytest.mark.parametrize(("return_code", "result_exists"), [(0, False), (1, True)])
def test_run_qa_streams_combined_output_and_manages_result_file(
    programmer: tuple[Programmer, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    return_code: int,
    result_exists: bool,
) -> None:
    instance, _, _ = programmer
    process = mock_process(["first line\n", "second line\n"], return_code)
    popen = MagicMock(name="Popen", return_value=process)
    monkeypatch.setattr("runners.programmer.subprocess.Popen", popen)

    succeeded = instance.run_qa("lint", "ruff check .")

    assert succeeded is (return_code == 0)
    assert capsys.readouterr().out == "first line\nsecond line\n"
    result_file = instance.ralph_dir / "lint-result.txt"
    assert result_file.exists() is result_exists
    if result_exists:
        assert result_file.read_text(encoding="utf-8") == "first line\nsecond line\n"
    popen.assert_called_once_with(
        "ruff check .",
        cwd=Path.cwd(),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    process.wait.assert_called_once_with()


def test_run_qa_raises_when_stdout_was_not_captured(
    programmer: tuple[Programmer, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance, _, _ = programmer
    popen = MagicMock(name="Popen", return_value=mock_process(None))
    monkeypatch.setattr("runners.programmer.subprocess.Popen", popen)

    with pytest.raises(RuntimeError, match="Could not capture output from typecheck"):
        instance.run_qa("typecheck", "mypy .")


@pytest.mark.parametrize(
    ("check_results", "expected"),
    [([True, True], True), ([False, True], False)],
)
def test_run_quality_checks_runs_configured_commands_and_combines_results(
    programmer: tuple[Programmer, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    check_results: list[bool],
    expected: bool,
) -> None:
    instance, _, _ = programmer
    instance.qa_commands = {
        QA.LINT: "ruff check .",
        QA.TYPECHECK: None,
        QA.TEST: "pytest",
    }
    run_qa = MagicMock(name="run_qa", side_effect=check_results)
    monkeypatch.setattr(instance, "run_qa", run_qa)

    assert instance.run_quality_checks() is expected
    assert run_qa.call_args_list == [call("lint", "ruff check ."), call("test", "pytest")]


def test_run_quality_checks_succeeds_when_no_commands_are_configured(
    programmer: tuple[Programmer, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance, _, _ = programmer
    instance.qa_commands = {qa: None for qa in QA}
    run_qa = MagicMock(name="run_qa")
    monkeypatch.setattr(instance, "run_qa", run_qa)

    assert instance.run_quality_checks() is True
    run_qa.assert_not_called()


def test_build_prompt_for_first_attempt_contains_story_details(
    programmer: tuple[Programmer, MagicMock, MagicMock],
    story: Story,
) -> None:
    instance, _, _ = programmer

    prompt = instance.build_prompt(story, iteration_num=1)

    assert (
        prompt
        == """Implement the following user story: Quality-check helpers

Description: Persist failed checks so retries have useful context.

Acceptance criteria:
 - Run every configured quality check
 - Include failed check output in retry context"""
    )


def test_build_prompt_for_retry_references_only_available_qa_results(
    programmer: tuple[Programmer, MagicMock, MagicMock],
    story: Story,
) -> None:
    instance, _, _ = programmer
    (instance.ralph_dir / "lint-result.txt").write_text("lint failed", encoding="utf-8")
    (instance.ralph_dir / "test-result.txt").write_text("tests failed", encoding="utf-8")

    prompt = instance.build_prompt(story, iteration_num=2)

    assert (
        prompt
        == """Fix errors in the implementation of the user story: Quality-check helpers

The lint checker found errors, its output is stored in the file `.ralph/lint-result.txt`.
The test checker found errors, its output is stored in the file `.ralph/test-result.txt`.

Acceptance criteria:
 - Run every configured quality check
 - Include failed check output in retry context"""
    )
