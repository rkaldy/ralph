# PRD: Unit Tests for Core Logic

## Introduction

Add a focused unit test suite for Ralph's core models, PRD design workflow, and story execution workflow. The suite will provide broad regression protection for observable behavior in `src/models.py`, `src/designer.py`, and `src/executor.py` while isolating Codex, subprocess, terminal, and filesystem boundaries with pytest test doubles.

## Goals

- Protect the core model, design, conversion, quality-check, and execution behaviors against regressions.
- Cover normal behavior, boundary conditions, and important failure paths with deterministic tests.
- Keep tests fast and independent of live Codex sessions, real shell commands, and user input.
- Make failures describe the behavior that regressed rather than internal implementation details.
- Ensure the complete unit test suite passes consistently in the repository's existing development environment.

## User Stories

### US-001: Test model validation and story selection

**Description:** As a maintainer, I want tests for the core data models so that schema and story-selection regressions are detected immediately.

**Acceptance Criteria:**

- [ ] Tests verify that `PRD.next_story()` returns the lowest-priority-number story whose `passes` value is false.
- [ ] Tests verify that passed stories are ignored, priority ties behave deterministically according to input order, and an all-passing or empty story list returns `None`.
- [ ] Tests do not depend on network access, subprocesses, or the user's filesystem.

### US-002: Test the interactive PRD design workflow

**Description:** As a maintainer, I want tests for `Designer.design()` so that interactive PRD sessions continue to prompt, complete, and fail as intended.

**Acceptance Criteria:**

- [ ] Tests verify that the initial Codex prompt contains the supplied feature description.
- [ ] Tests simulate one or more incomplete responses and verify that each user answer is sent back to the same mocked session.
- [ ] Tests verify that a completed response ends the prompt loop and prints the generated PRD path and follow-up execution command.
- [ ] Parameterized tests verify that both `CodexError` and `RalphError` are reported to stderr and converted to `typer.Exit` with exit code 1.
- [ ] Tests use mocks or fakes for Codex and terminal input; no live interactive session is started.

### US-003: Test Markdown PRD conversion

**Description:** As a maintainer, I want tests for `Designer.convert()` so that conversion results are accepted only when they target Ralph's expected JSON file.

**Acceptance Criteria:**

- [ ] Tests verify that the conversion prompt contains the supplied Markdown path and the expected `.ralph/prd.json` output path.
- [ ] Tests verify that an equivalent resolved output path is accepted and a completion message is printed.
- [ ] Tests verify that a missing or different response file raises the expected `RalphError`, which is reported and converted to `typer.Exit` with exit code 1.
- [ ] Parameterized tests cover `CodexError` and `RalphError` raised while entering or using the mocked session.
- [ ] Tests use a pytest temporary directory and do not modify the repository's real `.ralph` state.

### US-004: Test quality-check command handling

**Description:** As a maintainer, I want tests for executor quality checks so that command execution, output capture, and pass/fail aggregation remain reliable.

**Acceptance Criteria:**

- [ ] Tests verify that an empty quality-check command succeeds without starting a subprocess.
- [ ] Tests verify that a successful command streams combined output, returns true, and removes its temporary result file.
- [ ] Tests verify that a failed command returns false and retains its result file with the captured output.
- [ ] Tests verify that lint, type-check, and test commands are each invoked once and that `run_quality_checks()` returns true only when all three results are true.
- [ ] Subprocess behavior is mocked; tests do not execute real shell commands.

### US-005: Test story iteration and retry behavior

**Description:** As a maintainer, I want tests for individual execution iterations and retry limits so that story implementation is predictable and bounded.

**Acceptance Criteria:**

- [ ] Tests verify that `iteration()` builds a prompt containing the story title, description, and every acceptance criterion.
- [ ] Tests verify that a valid non-blocking execution response runs quality checks and returns their boolean result.
- [ ] Tests verify that an execution response containing a blocker raises `RalphError` and does not run quality checks.
- [ ] Tests verify that `implement_story()` removes stale quality-check result files, retries until checks pass, and prints a completion message once.
- [ ] Tests verify that repeated failures stop at `MAX_ITERATIONS` and raise `RalphError` without starting an additional iteration.
- [ ] Codex responses, quality checks, terminal output, and filesystem locations are controlled with pytest mocks and temporary paths.

### US-006: Test top-level execution orchestration

**Description:** As a maintainer, I want tests for `Executor.run()` so that PRD loading, session setup, story dispatch, and user-facing errors remain protected.

**Acceptance Criteria:**

- [ ] Tests verify that `.ralph/prd.json` is loaded and validated and `.ralph/progress.md` is initialized in an isolated temporary directory.
- [ ] Tests verify that incomplete stories returned by the PRD selection flow are passed to `implement_story()` in sequence and that processing stops when no story remains.
- [ ] Parameterized tests verify that supported filesystem, decoding, validation, Codex, and Ralph errors are reported to stderr and converted to `typer.Exit` with exit code 1.
- [ ] Tests do not start Codex, execute shell commands, or read or write the repository's real `.ralph` files.

## Functional Requirements

- FR-1: Unit tests must be written with `pytest`.
- FR-2: The suite must cover observable behavior in `src/models.py`, `src/designer.py`, and `src/executor.py`.
- FR-3: Tests must cover successful paths, boundary conditions, and explicitly handled failure paths described in the user stories.
- FR-4: Tests must replace Codex sessions, user input, subprocesses, and terminal output with mocks or lightweight fakes.
- FR-5: Tests that need filesystem access must use pytest-provided temporary directories and must not alter real `.ralph` files.
- FR-6: Tests must be deterministic and must not require network access, credentials, a live Codex process, or platform-specific shell behavior.
- FR-7: Assertions must focus on public outcomes and boundary interactions; private implementation details should be asserted only when required to verify a documented side effect.
- FR-8: The full test suite must pass when run with pytest in the existing development environment.
- FR-9: The change must not modify runtime source files, dependency declarations, task-runner configuration, or CI configuration.

## Non-Goals

- Testing modules outside `models.py`, `designer.py`, and `executor.py` in this phase.
- Adding integration, end-to-end, snapshot, performance, or browser tests.
- Connecting to the real Codex SDK or executing real lint, type-check, or test subprocesses from unit tests.
- Refactoring or fixing production behavior discovered while writing tests.
- Adding or changing pytest dependencies, coverage thresholds, test commands, CI workflows, or other automation.
- Requiring a numeric line-coverage percentage; completeness is based on the specified behaviors and failure paths.

## Technical Considerations

- Use pytest fixtures, `monkeypatch`, and `unittest.mock` where they keep setup concise and readable.
- Patch dependencies where they are imported by the module under test, such as `designer.CodexSession` and `executor.subprocess.Popen`.
- Use `tmp_path` and a controlled working directory for tests involving `.ralph` paths.
- Prefer small fake response and context-manager objects when they communicate session behavior more clearly than deeply nested mocks.
- Parameterize equivalent error cases to avoid repetitive test bodies while retaining descriptive case identifiers.
- Because project tooling and dependency files are out of scope, pytest availability is treated as a prerequisite of the development environment.

## Success Metrics

- Every acceptance criterion in US-001 through US-006 has at least one deterministic automated test.
- The suite exercises every explicitly handled error category in the selected modules.
- The tests make zero real network calls, Codex calls, or shell-command executions.
- Repeated local runs produce the same result and leave no test artifacts in the repository.
- The repository's existing lint and type-check commands continue to pass.

## Open Questions

- None. The agreed scope intentionally treats pytest as available and excludes dependency, command, coverage, and CI configuration changes.
