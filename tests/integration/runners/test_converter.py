import json
from pathlib import Path

from pytest_mock import MockerFixture

from ralph.config import RalphConfig
from ralph.runners.converter import Converter


def test_converter_happy_path(
    mocker: MockerFixture,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    mocker.patch("ralph.ui.console", autospec=True)

    prd_file = tmp_path / "offline-reading.md"
    prd_file.write_text(
        """# PRD: Offline Reading

## Overview

Let readers save articles and continue reading without a network connection.

## User Stories

### US-001: Save an article for offline reading
**Description:** As a reader, I want to save an article so I can read it without a connection.

**Acceptance Criteria:**
- [ ] Add a save-for-offline action to each article
- [ ] Store the article content on the device

### US-002: Open a saved article
**Description:** As a reader, I want to open saved articles while I am offline.

**Acceptance Criteria:**
- [ ] List every saved article in an offline library
- [ ] Open saved content when the network is unavailable
""",
        encoding="utf-8",
    )

    converter = Converter(RalphConfig.model_construct(), prd_file)

    converter.run()

    prd = json.loads((tmp_path / ".ralph" / "prd.json").read_text(encoding="utf-8"))
    assert prd == {
        "name": "Offline Reading",
        "branch_name": "offline-reading",
        "user_stories": [
            {
                "id": "US-001",
                "title": "Save an article for offline reading",
                "description": (
                    "As a reader, I want to save an article so I can read it without a connection."
                ),
                "priority": 1,
                "acceptance_criteria": [
                    "Add a save-for-offline action to each article",
                    "Store the article content on the device",
                ],
                "passes": False,
            },
            {
                "id": "US-002",
                "title": "Open a saved article",
                "description": "As a reader, I want to open saved articles while I am offline.",
                "priority": 2,
                "acceptance_criteria": [
                    "List every saved article in an offline library",
                    "Open saved content when the network is unavailable",
                ],
                "passes": False,
            },
        ],
    }

    progress = (tmp_path / ".ralph" / "progress.md").read_text(encoding="utf-8")
    assert "# PRD: Offline Reading" in progress
    assert "## Overview" in progress
    assert "Let readers save articles and continue reading without a network connection." in progress
    assert (
        "- **US-001: Save an article for offline reading** - As a reader, I want to save an "
        "article so I can read it without a connection."
    ) in progress
    assert (
        "- **US-002: Open a saved article** - As a reader, I want to open saved articles while I am offline."
    ) in progress
    assert "## Codebase Patterns" in progress
    assert "## Gotchas Encountered" in progress
