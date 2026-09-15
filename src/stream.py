import typer
from openai_codex.generated.v2_all import AgentMessageDeltaNotification
from pydantic import BaseModel

from ui import CODEX_OUTPUT, COMMAND_OUTPUT, INTRO_DARK, MONOSPACE


class CodexStreamOutput:
    """Write streamed Codex text while preserving Markdown bold spans."""

    COMPLETION_PREFIX = "<!-- ralph:complete "

    def __init__(self) -> None:
        self.bold = False
        self.monospace = False
        self.pending_star = False
        self.result_parts: list[str] = []
        self.pending_output = ""
        self.completion_marker_started = False
        self.payload_type: type[BaseModel] | None = None
        self.at_line_start = True

    def write(self, text: str, payload_type: type[BaseModel]) -> None:
        """Store a response delta and write its user-visible part."""
        self.result_parts.append(text)
        self.payload_type = payload_type

        if self.completion_marker_started:
            return

        self.pending_output += text
        marker_position = self.pending_output.find(self.COMPLETION_PREFIX)
        if marker_position >= 0:
            self._write_formatted(self.pending_output[:marker_position])
            self.pending_output = self.pending_output[marker_position:]
            self.completion_marker_started = True
            return

        overlap = 0
        overlap_limit = min(len(self.pending_output), len(self.COMPLETION_PREFIX) - 1)
        for length in range(overlap_limit, 0, -1):
            if self.pending_output.endswith(self.COMPLETION_PREFIX[:length]):
                overlap = length
                break

        if overlap:
            self._write_formatted(self.pending_output[:-overlap])
            self.pending_output = self.pending_output[-overlap:]
        else:
            self._write_formatted(self.pending_output)
            self.pending_output = ""

    def _write_formatted(self, text: str) -> None:
        rendered: list[str] = []
        segment: list[str] = []

        def flush() -> None:
            if not segment:
                return
            color: str | tuple[int, int, int]
            if self.monospace:
                color = MONOSPACE
            elif self.payload_type is AgentMessageDeltaNotification:
                color = CODEX_OUTPUT
            else:
                color = COMMAND_OUTPUT
            rendered.append(typer.style("".join(segment), fg=color, bold=self.bold))
            segment.clear()

        for character in text:
            if character == "`":
                if self.pending_star:
                    segment.append("*")
                    self.pending_star = False
                flush()
                self.monospace = not self.monospace
                continue

            if character == "*" and not self.monospace:
                if self.pending_star:
                    flush()
                    self.bold = not self.bold
                    self.pending_star = False
                else:
                    self.pending_star = True
                continue

            if self.pending_star:
                segment.append("*")
                self.pending_star = False
            segment.append(character)

        flush()
        if rendered:
            typer.echo("".join(rendered), nl=False)
            self.at_line_start = text.endswith("\n")

    def write_separator(self) -> None:
        """Draw a separator between consecutive Codex message items."""
        if not self.at_line_start:
            typer.echo()
        typer.echo(typer.style("\n• ", fg=INTRO_DARK, bold=True), nl=False)
        self.at_line_start = True

    def finish(self) -> None:
        """Flush pending text and finish the streamed output line."""
        if not self.completion_marker_started:
            self._write_formatted(self.pending_output)
        self.pending_output = ""

        if self.pending_star:
            color = CODEX_OUTPUT if self.payload_type is AgentMessageDeltaNotification else COMMAND_OUTPUT
            typer.echo(
                typer.style("*", fg=color, bold=self.bold),
                nl=False,
            )
            self.pending_star = False
        typer.echo("\n")

    @property
    def result(self) -> str:
        """Return the complete unformatted Codex response."""
        return "".join(self.result_parts)
