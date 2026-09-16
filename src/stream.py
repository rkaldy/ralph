import typer
from openai_codex.generated.v2_all import AgentMessageDeltaNotification
from pydantic import BaseModel

from ui import CODEX_OUTPUT, COMMAND_OUTPUT, INTRO_DARK, MONOSPACE


class CodexStreamOutput:
    """Write streamed Codex text while preserving Markdown bold spans."""

    def __init__(self) -> None:
        self.bold = False
        self.monospace = False
        self.pending_star = False
        self.payload_type: type[BaseModel] | None = None
        self.at_line_start = True

    def write(self, text: str, payload_type: type[BaseModel]) -> None:
        """Write a user-visible response delta."""
        self.payload_type = payload_type
        self._write_formatted(text)

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
        """Finish the streamed output line."""
        if self.pending_star:
            color = CODEX_OUTPUT if self.payload_type is AgentMessageDeltaNotification else COMMAND_OUTPUT
            typer.echo(
                typer.style("*", fg=color, bold=self.bold),
                nl=False,
            )
            self.pending_star = False
        typer.echo("\n")
