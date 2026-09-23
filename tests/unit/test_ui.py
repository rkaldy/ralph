import pytest
from openai_codex.generated.v2_all import CommandExecutionThreadItem
from pytest_mock import MockFixture
from rich.text import Text

from ralph.ui import LinePreservingMarkdown, LiveRow, format_command


@pytest.fixture
def live_mock(mocker: MockFixture):
    live_class_mock = mocker.patch("ralph.ui.Live", autospec=True)
    return live_class_mock.return_value


def command_item(*actions: dict[str, object]) -> CommandExecutionThreadItem:
    return CommandExecutionThreadItem.model_validate(
        {
            "type": "commandExecution",
            "id": "command",
            "command": "",
            "commandActions": actions,
            "cwd": ".",
            "status": "completed",
        }
    )


def test_line_preserving_markdown() -> None:
    markdown = LinePreservingMarkdown("first line\nsecond line", style="reasoning")

    token_types = [token.type for token in markdown._flatten_tokens(markdown.parsed)]

    assert "softbreak" not in token_types
    assert token_types.count("hardbreak") == 1


def test_live_row(live_mock) -> None:
    row = LiveRow(initial_buffering=5)

    live_mock.start.assert_called_once_with()

    row.update("hello")
    live_mock.update.assert_not_called()

    row.start(" world", style="reasoning")

    rendered = live_mock.update.call_args.args[0]
    assert isinstance(rendered, LinePreservingMarkdown)
    assert rendered.markup == "hello world"
    assert rendered.style == "reasoning"
    assert row.match("lo wo") is True
    assert row.match("missing") is False

    row.clear()
    assert row.buffer == ""
    assert row.match("hello") is False

    replacement = Text("Finished", style="meta")
    row.text(replacement)
    live_mock.update.assert_called_with(replacement)
    live_mock.stop.assert_called_once_with()

    row.stop()
    assert live_mock.stop.call_count == 2


def test_format_command() -> None:
    item = command_item(
        {"type": "read", "command": "cat src/ui.py", "name": "ui.py", "path": "src/ui.py"},
        {"type": "search", "command": "rg prompt src", "query": "prompt", "path": "src"},
        {"type": "search", "command": "rg"},
        {"type": "listFiles", "command": "find tests", "path": "tests"},
        {"type": "listFiles", "command": "find"},
        {"type": "unknown", "command": '/bin/bash -lc "printf hello"'},
        {"type": "unknown", "command": "git status --short"},
    )

    formatted = format_command(item)

    assert formatted.plain == (
        "Read ui.py\n"
        "Search prompt in src\n"
        "Search ? in ?\n"
        "List tests\n"
        "List .\n"
        "Run printf hello\n"
        "Run git status --short\n"
    )
