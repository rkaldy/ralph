from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from ralph.app import app
from ralph.config import RalphConfig


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def designer_mock(mocker: MockerFixture):
    mocker.patch("ralph.app.RalphConfig", return_value=RalphConfig.model_construct())
    return mocker.patch("ralph.app.Designer", autospec=True)


def test_designer_accepts_feature_argument(runner: CliRunner, designer_mock) -> None:
    result = runner.invoke(app, ["designer", "Add task priorities"])

    assert result.exit_code == 0
    designer_mock.assert_called_once_with(designer_mock.call_args.args[0], "Add task priorities")
    designer_mock.return_value.run.assert_called_once_with()


def test_designer_reads_feature_from_file(
    runner: CliRunner,
    designer_mock,
    tmp_path: Path,
) -> None:
    feature_file = tmp_path / "feature.txt"
    feature_file.write_text("  Add task priorities\nwith custom ordering.\n", encoding="utf-8")

    result = runner.invoke(app, ["designer", "--file", str(feature_file)])

    assert result.exit_code == 0
    designer_mock.assert_called_once_with(
        designer_mock.call_args.args[0],
        "Add task priorities\nwith custom ordering.",
    )
    designer_mock.return_value.run.assert_called_once_with()


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ([], "Provide FEATURE or --file"),
        (["A feature", "--file", "feature.txt"], "Provide FEATURE or --file, not both"),
    ],
)
def test_designer_requires_exactly_one_feature_source(
    runner: CliRunner,
    designer_mock,
    tmp_path: Path,
    arguments: list[str],
    message: str,
) -> None:
    feature_file = tmp_path / "feature.txt"
    feature_file.write_text("Feature from file", encoding="utf-8")
    arguments = [str(feature_file) if argument == "feature.txt" else argument for argument in arguments]

    result = runner.invoke(app, ["designer", *arguments])

    assert result.exit_code == 2
    assert message in result.output
    designer_mock.assert_not_called()


def test_designer_rejects_empty_feature_file(
    runner: CliRunner,
    designer_mock,
    tmp_path: Path,
) -> None:
    feature_file = tmp_path / "empty.txt"
    feature_file.write_text(" \n", encoding="utf-8")

    result = runner.invoke(app, ["designer", "--file", str(feature_file)])

    assert result.exit_code == 2
    assert "Feature description must not be empty" in result.output
    designer_mock.assert_not_called()
