# PRD: Add Ruff Linter and Formatter

## 1. Introduction/Overview

Add Ruff as the project's standard Python linter and formatter. The repository currently has no configured linting, formatting, pre-commit, or task-runner workflow. This feature will establish consistent automated code-quality checks for Python 3.12 development while keeping enforcement local: developers can run checks through a Makefile, and pre-commit hooks will automatically fix lint issues and format staged Python files.

The rollout should focus on tooling and configuration. Existing source files may receive only the minimal linting or formatting changes required for every newly introduced check to pass when the feature lands.

## 2. Goals

- Add Ruff as the single tool for Python linting, import sorting, and formatting.
- Give developers memorable `make` commands for linting, formatting, and non-mutating validation.
- Automatically fix supported lint violations and format Python files during pre-commit.
- Start with a focused, low-friction lint rule set: `E4`, `E7`, `E9`, `F`, and `I`.
- Ensure all new checks pass across the repository immediately after rollout.
- Keep Ruff enforcement out of CI for this feature.

## 3. User Stories

### US-001: Configure Ruff

**Description:** As a developer, I want a shared Ruff configuration so that Python code is checked and formatted consistently.

**Acceptance Criteria:**

- [ ] Ruff is declared as a development dependency in `pyproject.toml` and resolved in `uv.lock`.
- [ ] Ruff targets Python 3.12, matching the project's minimum supported Python version.
- [ ] Ruff linting enables exactly the initial rule families `E4`, `E7`, `E9`, `F`, and `I`, apart from any rules Ruff necessarily enables by default and explicitly documents in its effective configuration.
- [ ] Ruff's formatter is configured or its documented defaults are intentionally used.
- [ ] Lint and formatter settings are stored in `pyproject.toml` rather than a separate Ruff configuration file.
- [ ] Ruff does not scan generated, virtual-environment, cache, or version-control directories.
- [ ] `uv lock --check` succeeds after dependency changes.

### US-002: Add local Makefile commands

**Description:** As a developer, I want simple project commands so that I do not need to remember Ruff's command-line arguments.

**Acceptance Criteria:**

- [ ] A `Makefile` provides a `lint` target that runs a non-mutating Ruff lint check across all repository Python files.
- [ ] A `format` target applies Ruff formatting across all repository Python files.
- [ ] A `check` target runs both the non-mutating lint check and Ruff's non-mutating formatting check.
- [ ] Each target executes Ruff through `uv run`, using the repository's locked development environment.
- [ ] The targets are declared phony and return a non-zero exit status when their underlying checks fail.
- [ ] `make lint`, `make format`, and `make check` complete successfully after the rollout.

### US-003: Enforce Ruff with pre-commit

**Description:** As a developer, I want Ruff to fix and format staged Python files before commit so that routine style cleanup happens automatically.

**Acceptance Criteria:**

- [ ] `pre-commit` is declared as a development dependency in `pyproject.toml` and resolved in `uv.lock`.
- [ ] A root `.pre-commit-config.yaml` configures the official Ruff pre-commit hooks.
- [ ] The lint hook runs with safe automatic fixes enabled.
- [ ] The formatter hook runs after the lint hook so import and lint fixes are formatted in their final form.
- [ ] Hooks apply to Python and Python stub files supported by Ruff.
- [ ] When a hook modifies a file, pre-commit reports the change and requires the developer to review, restage, and retry the commit.
- [ ] `uv run pre-commit run --all-files` succeeds after the rollout.

### US-004: Establish a clean baseline

**Description:** As a maintainer, I want the new checks to start green so that future failures represent newly introduced problems.

**Acceptance Criteria:**

- [ ] Existing Python files receive only changes required by the selected Ruff lint rules or formatter.
- [ ] Unrelated refactors, renames, and behavior changes are excluded from cleanup.
- [ ] Application behavior and public CLI behavior remain unchanged.
- [ ] `make check` succeeds with no file modifications.
- [ ] Running `uv run pre-commit run --all-files` a second time succeeds without modifying files.

### US-005: Document the developer workflow

**Description:** As a developer, I want concise setup and usage instructions so that I can install and run the tooling correctly.

**Acceptance Criteria:**

- [ ] Developer documentation explains how to synchronize development dependencies with `uv`.
- [ ] Documentation explains `make lint`, `make format`, and `make check` and distinguishes mutating from non-mutating commands.
- [ ] Documentation explains how to install the pre-commit hooks locally.
- [ ] Documentation states that CI enforcement is not included in this rollout.
- [ ] Every documented command matches the committed configuration and succeeds from the repository root.

## 4. Functional Requirements

- **FR-1:** The project must manage Ruff and pre-commit as development-only dependencies through `uv`.
- **FR-2:** Ruff configuration must live under the appropriate `[tool.ruff]` tables in `pyproject.toml`.
- **FR-3:** Ruff must target Python 3.12.
- **FR-4:** Ruff linting must initially cover pycodestyle errors in the `E4`, `E7`, and `E9` groups, Pyflakes rules (`F`), and isort-compatible import rules (`I`).
- **FR-5:** Ruff must provide both lint checking and code formatting.
- **FR-6:** `make lint` must run Ruff linting without modifying files.
- **FR-7:** `make format` must apply Ruff formatting.
- **FR-8:** `make check` must run linting and formatting validation without modifying files.
- **FR-9:** Pre-commit must run Ruff linting with automatic fixes before running Ruff formatting.
- **FR-10:** Pre-commit must operate on supported staged Python files and use the repository's shared Ruff configuration.
- **FR-11:** The implementation must make the entire current repository pass `make check` and a full pre-commit run.
- **FR-12:** Baseline source cleanup must be limited to changes emitted by Ruff or directly required to resolve an enabled Ruff violation.
- **FR-13:** The feature must include concise developer instructions for dependency setup, hook installation, manual formatting, and non-mutating checks.
- **FR-14:** No GitHub Actions or other CI configuration may be added or changed to enforce Ruff.

## 5. Non-Goals (Out of Scope)

- CI or pull-request enforcement.
- Enabling Ruff's `ALL` rule set.
- Enabling pyupgrade (`UP`), flake8-bugbear (`B`), or flake8-simplify (`SIM`) rules in the initial rollout.
- Introducing Black, isort, Flake8, or another overlapping formatter or linter.
- Broad refactoring or behavioral changes to existing Python code.
- Adding a Justfile or Python console-script wrappers for lint tasks.
- Automatically committing hook-generated changes.
- Applying formatting rules to non-Python file types.

## 6. Technical Considerations

- Use Ruff's native formatter and import-sorting support to avoid overlapping tools.
- Preserve Ruff's default formatting conventions unless an existing repository convention demonstrably requires an explicit override. Any override must be documented in `pyproject.toml` or the developer documentation.
- Configure the official `ruff-pre-commit` repository with the `ruff-check` hook using `--fix`, followed by `ruff-format`. Pin hook revisions according to pre-commit's normal reproducibility model.
- Keep Makefile commands and pre-commit behavior aligned with the same `pyproject.toml` configuration.
- The repository contains uncommitted work at planning time. Implementation must preserve unrelated working-tree changes and restrict baseline cleanup to Ruff-required edits.

## 7. Success Metrics

- `make lint` exits successfully on the completed repository.
- `make check` exits successfully without changing any files.
- `uv run pre-commit run --all-files` exits successfully; an immediate second run produces no file changes.
- A deliberately introduced unused import is rejected or automatically removed by the lint workflow.
- A deliberately misordered import is corrected by the pre-commit lint hook.
- A deliberately misformatted Python file is reformatted by the pre-commit formatter hook and rejected for restaging.
- No CI workflow is introduced or modified.

## 8. Open Questions

None. The initial enforcement location, lint rule scope, formatter adoption, baseline policy, pre-commit behavior, and developer command interface were resolved during requirements gathering.
