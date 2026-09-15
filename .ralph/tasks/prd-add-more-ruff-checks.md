# PRD: Add More Ruff Checks

## 1. Introduction/Overview

Expand the repository's Ruff lint configuration from the current selected families (`E`, `F`, `I`, `UP`, `B`, and `SIM`) to Ruff's stable `ALL` preset. The change should maximize static code-quality coverage while retaining Ruff as both linter and formatter, keeping the existing auto-fixing `make lint` workflow, and avoiding formatter conflicts or rules that cannot be applied responsibly to this repository.

The implementation must leave the current repository green. It may change Python source only as needed to satisfy the expanded checks and must not introduce pre-commit or CI enforcement.

## 2. Goals

- Enable all stable Ruff lint rules through `select = ["ALL"]`.
- Explicitly exclude only rules that conflict with Ruff's formatter or have a documented repository-specific justification.
- Resolve every violation produced by the resulting effective rule set across the repository.
- Preserve the existing auto-formatting and auto-fixing behavior of `make lint`.
- Keep application behavior and the public CLI unchanged.
- Make repeated lint runs deterministic and clean.

## 3. User Stories

### US-001: Enable the comprehensive Ruff rule set

**Description:** As a maintainer, I want Ruff's stable `ALL` preset enabled so that the project benefits from new correctness, security, maintainability, and consistency checks.

**Acceptance Criteria:**

- [ ] `[tool.ruff.lint]` in `pyproject.toml` uses `select = ["ALL"]` instead of enumerating the current rule families.
- [ ] Ruff preview mode remains disabled; unstable preview rules are not part of this feature.
- [ ] The configuration explicitly ignores the formatter-incompatible rules Ruff currently recommends disabling: `W191`, `E111`, `E114`, `E117`, `D203`, `D206`, `D300`, `Q000`, `Q001`, `Q002`, `Q003`, `Q004`, `COM812`, `COM819`, and `ISC002`.
- [ ] `D213` is explicitly ignored in favor of `D212`, avoiding Ruff's mutually exclusive pydocstyle convention warning.
- [ ] Any additional global, file-level, or line-level ignore includes a nearby comment explaining why the rule is unsuitable at that scope.
- [ ] `uv run ruff check .` emits no rule-conflict or formatter-compatibility warnings.
- [ ] `uv run mypy` succeeds.

### US-002: Establish a clean expanded-rule baseline

**Description:** As a developer, I want the repository to pass the expanded lint configuration immediately so that future failures identify newly introduced issues.

**Acceptance Criteria:**

- [ ] Every Python file in Ruff's configured scope passes `uv run ruff check .`.
- [ ] Missing annotations, docstrings, exception-message issues, naming findings, and other violations from the expanded effective rule set are fixed or narrowly suppressed with a documented justification.
- [ ] The intentional `›` character used by the terminal interface may be retained through a narrow suppression rather than changing the visible interface solely to satisfy `RUF001`.
- [ ] A repository-wide rule is not disabled merely to avoid correcting a violation in one file when a narrower, understandable fix or suppression is available.
- [ ] Source edits do not alter command names, prompts, output semantics, exit behavior, configuration keys, or Codex session behavior.
- [ ] No unrelated refactoring, renaming, dependency update, or reformatting of non-Python files is included.
- [ ] `uv run ruff format --check .` succeeds.
- [ ] `uv run mypy` succeeds.

### US-003: Preserve the local auto-fixing workflow

**Description:** As a developer, I want `make lint` to continue applying safe Ruff fixes and formatting so that the stricter rules do not change my established workflow.

**Acceptance Criteria:**

- [ ] `make lint` continues to run Ruff formatting, Ruff linting with safe automatic fixes, and mypy.
- [ ] The workflow does not enable Ruff's unsafe fixes globally.
- [ ] Running `make lint` on the completed repository succeeds.
- [ ] Running `make lint` a second time succeeds without modifying tracked files.
- [ ] No pre-commit configuration or CI workflow is added or changed.

## 4. Functional Requirements

- **FR-1:** Ruff must select the stable `ALL` rule preset in `pyproject.toml`.
- **FR-2:** Ruff preview mode must remain disabled.
- **FR-3:** The configuration must explicitly ignore Ruff rules that conflict with the Ruff formatter, as listed in US-001.
- **FR-4:** The configuration must select `D212` over the incompatible `D213` docstring convention.
- **FR-5:** All other exclusions must use the narrowest practical scope and include a written justification in the configuration or source.
- **FR-6:** The intentional terminal UI glyph flagged by `RUF001` may receive a targeted suppression if preserving it is necessary to keep output unchanged.
- **FR-7:** All violations in the resulting effective rule set must be resolved throughout the current repository.
- **FR-8:** Safe automatic fixes may be used; unsafe fixes must be reviewed and applied manually rather than enabled wholesale.
- **FR-9:** `make lint` must retain its current mutating workflow: format the repository, apply safe lint fixes, then run mypy.
- **FR-10:** The completed repository must pass `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy`.
- **FR-11:** A second `make lint` run must be idempotent and leave tracked files unchanged.
- **FR-12:** Runtime behavior and the user-visible CLI contract must remain unchanged.

## 5. Non-Goals (Out of Scope)

- Enabling Ruff preview mode or preview-only rules.
- Adding pre-commit hooks.
- Adding or modifying CI workflows.
- Changing `make lint` into a non-mutating command or adding new Makefile targets.
- Enabling unsafe fixes globally.
- Adding another formatter, linter, or documentation tool.
- Broad refactoring, API redesign, CLI changes, or dependency upgrades.
- Adding developer documentation unrelated to comments that justify lint exclusions.
- Formatting or linting non-Python file types.

## 6. Technical Considerations

- The repository targets Python 3.12 and currently uses Ruff 0.16.7 or newer from its development dependency group.
- Ruff's `ALL` selector intentionally grows when Ruff adds stable rules. Future Ruff upgrades may therefore introduce new findings and should be reviewed rather than silently ignored.
- A baseline run with the current toolchain reports 40 findings before exclusions, including documentation, annotation, exception-message, naming, copyright, trailing-comma, and ambiguous-Unicode rules. Eight are safely auto-fixable; the remainder require deliberate edits or narrow suppressions.
- Formatter-conflicting lint rules must be ignored so `ruff format` cannot create violations that `ruff check` then rejects.
- Ruff automatically resolves some mutually exclusive pydocstyle rules, but explicit convention choices are required to avoid warnings and make project intent clear.
- Copyright checks require ownership and notice policy that the repository does not currently declare. If `CPY001` cannot be satisfied with an existing authoritative notice, exclude it globally with that justification rather than inventing ownership text.
- Renaming a public exception class solely for `N818` can affect consumers. Prefer a narrow suppression if compatibility cannot be proven; do not change the public API as part of this lint-only feature.

## 7. Success Metrics

- `uv run ruff check .` exits successfully with no warnings.
- `uv run ruff format --check .` exits successfully.
- `uv run mypy` exits successfully.
- `make lint` exits successfully and an immediate second run produces no tracked-file changes.
- All stable Ruff rule families are enabled except for explicitly documented compatibility or repository-specific exclusions.
- No pre-commit or CI files are added or changed.
- Existing automated tests, if present, continue to pass without behavior-oriented test updates.

## 8. Open Questions

None. Rule breadth, baseline policy, local workflow behavior, enforcement location, and implementation scope were resolved during requirements gathering.
