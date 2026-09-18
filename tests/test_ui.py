from collections.abc import Iterator
from unittest.mock import MagicMock, call

import pytest
import typer
from openai_codex.generated.v2_all import CommandExecutionThreadItem
from rich.text import Text

import ui
from exceptions import RalphError


@pytest.fixture
def live_double(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    live = MagicMock(name="live")
    factory = MagicMock(name="Live", return_value=live)
    monkeypatch.setattr(ui, "Live", factory)
    return factory, live


@pytest.fixture
def console_double(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    console = MagicMock(name="console")
    console.width = 20
    console.file = MagicMock(name="console_file")
    monkeypatch.setattr(ui, "console", console)
    return console


def flattened_token_types(markdown: ui.LinePreservingMarkdown) -> Iterator[str]:
    return (token.type for token in markdown._flatten_tokens(markdown.parsed))


def assert_terminal_style_restored(console: MagicMock) -> None:
    console.file.write.assert_has_calls(
        [
            call(typer.style("", fg="bright_white", bg=(32, 32, 32), reset=False)),
            call(typer.style("", reset=True)),
        ]
    )
    assert console.file.write.call_args_list[-1] == call(typer.style("", reset=True))
    assert console.print.call_args_list[-2:] == [call(), call()]


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


def test_line_preserving_markdown_turns_soft_breaks_into_hard_breaks() -> None:
    markdown = ui.LinePreservingMarkdown("first line\nsecond line", style="reasoning")

    token_types = list(flattened_token_types(markdown))

    assert "softbreak" not in token_types
    assert token_types.count("hardbreak") == 1


def test_live_row_buffers_and_controls_live_content(
    live_double: tuple[MagicMock, MagicMock],
) -> None:
    factory, live = live_double
    row = ui.LiveRow(initial_buffering=5)

    factory.assert_called_once()
    live.start.assert_called_once_with()

    row.update("hello")
    live.update.assert_not_called()

    row.start(" world", style="reasoning")

    rendered = live.update.call_args.args[0]
    assert isinstance(rendered, ui.LinePreservingMarkdown)
    assert rendered.markup == "hello world"
    assert rendered.style == "reasoning"
    assert row.match("lo wo") is True
    assert row.match("missing") is False

    row.clear()
    assert row.buffer == ""
    assert row.match("hello") is False

    replacement = Text("Finished", style="meta")
    row.text(replacement)
    live.update.assert_called_with(replacement)
    live.stop.assert_called_once_with()

    row.stop()
    assert live.stop.call_count == 2


def test_prompt_user_returns_console_input_and_restores_style(console_double: MagicMock) -> None:
    console_double.input.return_value = "continue"

    assert ui.prompt_user() == "continue"

    console_double.input.assert_called_once_with()
    console_double.file.flush.assert_called_once_with()
    assert_terminal_style_restored(console_double)


def test_prompt_user_translates_eof_and_restores_style(console_double: MagicMock) -> None:
    interruption = EOFError()
    console_double.input.side_effect = interruption

    with pytest.raises(RalphError, match="^Interrupted$") as raised:
        ui.prompt_user()

    assert raised.value.__cause__ is interruption
    assert_terminal_style_restored(console_double)


def test_prompt_user_restores_style_when_input_raises_an_unexpected_error(
    console_double: MagicMock,
) -> None:
    failure = RuntimeError("input failed")
    console_double.input.side_effect = failure

    with pytest.raises(RuntimeError, match="input failed") as raised:
        ui.prompt_user()

    assert raised.value is failure
    assert_terminal_style_restored(console_double)


def test_format_command_describes_supported_and_generic_actions() -> None:
    item = command_item(
        {"type": "read", "command": "cat src/ui.py", "name": "ui.py", "path": "src/ui.py"},
        {"type": "search", "command": "rg prompt src", "query": "prompt", "path": "src"},
        {"type": "search", "command": "rg"},
        {"type": "listFiles", "command": "find tests", "path": "tests"},
        {"type": "listFiles", "command": "find"},
        {"type": "unknown", "command": '/bin/bash -lc "printf hello"'},
        {"type": "unknown", "command": "git status --short"},
    )

    formatted = ui.format_command(item)

    assert formatted.plain == (
        "Read ui.py\n"
        "Search prompt in src\n"
        "Search ? in ?\n"
        "List tests\n"
        "List .\n"
        "Run printf hello\n"
        "Run git status --short\n"
    )
