# Ralph

Ralph is a Python command-line orchestrator that uses [OpenAI Codex](https://developers.openai.com/codex/) to turn a feature idea into a Product Requirements Document (PRD) and then implement it one user story at a time.

It is inspired by the original [Ralph](https://github.com/snarktank/ralph), but uses Codex instead of Amp/ClaudeCode and enforces a stricter QA loop.

It provides a three-stage workflow:

1. `designer` runs an interactive Codex session and writes a Markdown PRD.
2. `converter` converts that PRD into ordered, machine-readable user stories.
3. `programmer` implements each story, runs the configured quality checks, retries failures, and commits successful work.

Ralph stores its working state in `.ralph/`, so interrupted runs can continue with the next incomplete story.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- A working [Codex](https://openai.com/codex/) configuration and authentication
- A Git repository for the project Ralph will modify

Model defaults are read from `ralph.ini` file. If not set, use the user's model settings in `~/.codex/config.toml`.

## Installation

Ralph is packaged as the Python package `ralph`. The recommended way to install its CLI in an isolated
environment is directly from GitHub with `uv tool`:

```console
uv tool install git+https://github.com/rkaldy/ralph.git
```

This installs the `ralph` command, its Python package, and the bundled Codex skills. 

To install a local checkout while developing Ralph, use an editable tool installation:

```console
git clone git@github.com:rkaldy/ralph.git
uv tool install --editable ./ralph
```

Changes made in that checkout are then reflected in the installed command without reinstalling it. Use `uv tool uninstall ralph` to remove the command.

## Quick start

Create a `ralph.ini` file in the project root directory.

```ini
LINT_COMMAND=uv run ruff check .
TYPECHECK_COMMAND=uv run mypy
TEST_COMMAND=uv run pytest
```

Then run the workflow from that project:

```console
# 1. Describe and refine the feature interactively.
ralph designer "Add task priorities"

# 2. Review the generated PRD, then convert it.
ralph converter .ralph/tasks/prd-task-priorities.md

# 3. Implement all stories that have not passed yet.
ralph programmer
```

## Commands

### Designer

```bash
ralph designer FEATURE
```
or
```bash
ralph designer -f <feature-file>
```

Starts an interactive requirements session for a high-level feature description. Codex asks clarifying questions and splits the feature into stories.
Stories are small enough for one focused Codex session and ordered so that dependencies are implemented first.

The result is written into a PRD:

```text
.ralph/tasks/prd-<feature-name>.md
```
Review and edit the PRD before continuing.

### Converter

```bash
ralph converter .ralph/tasks/<prd-file>
```

Parses a Ralph-formatted Markdown PRD and creates:

- `.ralph/prd.json` — ordered user stories and their completion state
- `.ralph/progress.md` — shared project context, patterns, and gotchas

Story headings, descriptions, and unchecked acceptance-criteria items are converted directly into JSON. Other PRD sections are preserved in `progress.md` as implementation context.

### Programmer

```bash
ralph programmer
```

Loads `.ralph/prd.json`, switches to or creates the PRD's Git branch, and processes incomplete stories in priority order. For every story Ralph:

1. starts a fresh Codex thread with the programmer skill;
2. asks Codex to implement the story and its acceptance criteria;
3. runs the configured lint, type-check, and test commands;
4. if some of QA runs from the Step 3 fails, jump to Step 2 into another iteration, up to `MAX_ITERATIONS`;
5. updates `.ralph/progress.md` and marks the story as passed; and
6. stages all changes and creates a Git commit named after the story.

Failed check output is stored in `.ralph/lint-result.txt`, `.ralph/typecheck-result.txt`, or `.ralph/test-result.txt` so the next iteration can diagnose it. Successful results are removed.

Running `ralph programmer` again resumes at the highest-priority story whose `passes` value is `false`.

> [!WARNING]
> The programmer command can modify files, switch or create a Git branch, run shell commands from `ralph.ini`, stage all current changes with `git add --all`, and create commits. Run it only in a repository whose configuration and working tree you have reviewed.

## Configuration

Ralph reads case-sensitive settings from `ralph.ini` in the current working directory. Environment variables with the same names take precedence.

| Setting | Default | Description                                        |
| --- | --- |----------------------------------------------------|
| `LINT_COMMAND` | disabled | Shell command run as the lint check                |
| `TYPECHECK_COMMAND` | disabled | Shell command run as the type-check check          |
| `TEST_COMMAND` | disabled | Shell command run as the test check                |
| `SHOW_COMMANDS` | `false` | Show commands executed by Codex in the terminal UI |
| `MAX_ITERATIONS` | `5` | Maximum error fix attempts per story               |
| `GPT_MODEL_DESIGNER` | Codex user config | Model used during PRD design                       |
| `GPT_REASONING_DESIGNER` | Codex user config | Reasoning effort used during PRD design            |
| `GPT_MODEL_PROGRAMMER` | Codex user config | Model used during implementation                   |
| `GPT_REASONING_PROGRAMMER` | Codex user config | Reasoning effort used during implementation        |

## Generated files

```text
.ralph/
├── prd.json                 # Story definitions and completion state
├── progress.md              # Shared requirements and accumulated knowledge
├── tasks/                   # Markdown PRDs created by the designer
├── lint-result.txt          # Present only after a failed lint check
├── typecheck-result.txt     # Present only after a failed type check
└── test-result.txt          # Present only after a failed test check
```

## Development

Clone the repository and install the development dependencies:

```console
git clone <repository-url> ralph
cd ralph
uv sync
```

Run Ralph from the checkout with `uv run ralph` (or `uv run python -m ralph`), or expose that checkout
globally with `uv tool install --editable .`. Use the Makefile targets for local validation:

```console
make lint
make test
```

## License

Ralph is distributed under the [BSD 3-Clause License](LICENSE).
