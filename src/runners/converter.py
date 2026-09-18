import re
from dataclasses import dataclass, field
from pathlib import Path

import ui
from config import RalphConfig
from models import PRD, Story


@dataclass
class MarkdownChapter:
    text: list[str] = field(default_factory=list)
    chapters: dict[str, "MarkdownChapter"] = field(default_factory=dict)


class Converter:
    HEADING = re.compile(r"(#{1,6}) (.*)\n")
    USER_STORY = re.compile(r"([A-Z0-9\-]*): (.*)")

    def __init__(self, config: RalphConfig, prd_file: Path) -> None:
        self.prd_file = prd_file
        self.prd_markdown = MarkdownChapter()

    def parse_markdown(self) -> None:
        prd_text = self.prd_file.read_text(encoding="utf-8")
        stack: list[MarkdownChapter] = [self.prd_markdown]

        for line in prd_text.splitlines(keepends=True):
            heading = self.HEADING.fullmatch(line)
            if heading is None:
                stack[-1].text.append(line)  # noqa
            else:
                level = len(heading.group(1))
                title = heading.group(2)
                stack = stack[:level]
                if title in stack[-1].chapters:
                    raise ValueError(f"Duplicate Markdown heading '{title}'")
                chapter = MarkdownChapter()
                stack[-1].chapters[title] = chapter
                stack.append(chapter)

    def create_prd_json(self) -> None:
        title, contents = next(iter(self.prd_markdown.chapters.items()))
        name = title.removeprefix("PRD: ")
        prd = PRD(name=name, branch_name=name.lower().replace(" ", "-"), user_stories=[])

        priority = 1
        for heading, story in contents.chapters["User Stories"].chapters.items():
            heading_match = self.USER_STORY.match(heading)
            if not heading_match:
                raise ValueError(f"Malformed user story heading '{heading}'")
            description = next(line for line in story.text if line.startswith("**Description:**"))
            prd.user_stories.append(
                Story(
                    id=heading_match.group(1),
                    title=heading_match.group(2),
                    description=description.removeprefix("**Description:**").strip(),
                    priority=priority,
                    acceptance_criteria=[
                        line.removeprefix("- [ ]").strip() for line in story.text if line.startswith("- [ ] ")
                    ],
                    passes=False,
                )
            )
            priority += 1

        json_file = Path(".ralph/prd.json")
        json_file.write_text(prd.model_dump_json(indent=2), encoding="utf-8")
        ui.console.print(
            f"\nConversion completed. The generated JSON is at [bold]{json_file}[/bold]", style="meta"
        )

    def create_progress_file(self) -> None:
        with open(Path(".ralph/progress.md"), "w") as progress_file:
            title, contents = next(iter(self.prd_markdown.chapters.items()))
            progress_file.write(f"# {title}\n")
            progress_file.writelines(contents.text)
            for heading, chapter in contents.chapters.items():
                if heading != "User Stories":
                    progress_file.write(f"## {heading}\n")
                    progress_file.writelines(chapter.text)
            progress_file.write("\n## Codebase Patterns\n\n## Gotchas Encountered\n")

        ui.console.print(f"Progress initialized at [bold]{progress_file.name}[/bold]", style="meta")

    def run(self) -> None:
        self.parse_markdown()
        self.create_prd_json()
        self.create_progress_file()
        ui.console.print("Now run [bold]ralph programmer[/bold]\n", style="meta")
