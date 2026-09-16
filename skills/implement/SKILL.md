---
name: "implement"
description: "Implement or repair one Ralph user story selected by the orchestrator from `.ralph/prd.json`, including follow-up iterations for lint, typecheck, or test failures."
---

# Ralph Story Implementation

Implement the single user story identified in the current prompt. Keep the change focused on that story and its acceptance criteria.

## Context

- Follow all applicable `AGENTS.md` instructions in the workspace.
- Read the selected story in `.ralph/prd.json` for its complete requirements and acceptance criteria.
- Read all the **Codebase Patterns** and **Gotchas encountered** sections in `.ralph/progress.md`, if the file exists, before making changes.
- Inspect the relevant code and follow established project patterns.
- Use the original PRD only for global requirements, non-goals, technical constraints, terminology, and dependencies relevant to the selected story.
- Other stories in the original PRD are context, not additional implementation scope.

If the requested story cannot be found or its requirements are contradictory, report the blocker instead of selecting or implementing a different story.

## Previous Quality-check Failures

Before making changes, read any of these files that exist:

- `.ralph/lint-result.txt`: the orchestrator's linter output; its presence means lint failed.
- `.ralph/typecheck-result.txt`: the orchestrator's typecheck output; its presence means type checking failed.
- `.ralph/test-result.txt`: the orchestrator's test output; its presence means tests failed.

Use their output to diagnose and fix the reported errors as part of the selected story. If a reported failure is unrelated to the story or cannot be fixed safely within its scope, report it as a blocker. Do not create, modify, or delete these files; the Ralph orchestrator owns them.

## Implementation

- Implement only the selected story.
- Include tests when the story changes behavior and the project has an applicable test suite.
- Keep changes minimal and avoid unrelated refactoring.
- You may run focused checks or specific tests while developing, when they provide useful feedback. But the Ralph orchestrator runs the authoritative lint, typecheck, and test commands after your turn.

## Quality Requirements

- Keep changes focused and minimal
- Follow existing code patterns

## Orchestrator-owned State

Do not perform any of the following:

- Select another story or decide that the overall PRD is complete.
- Create, switch, or otherwise manage Git branches.
- Stage changes or create Git commits.
- Make any changes in `.ralph/prd.json` or `.ralph/progress.md`
- Treat checks run during this turn as the final project quality gate.

## Final Result

Return the implementation summary through the structured result supplied by
the orchestrator. Do not write a separate result file.

- `description` briefly explains what was implemented.
- `files` lists every changed file.
- `patterns` contains reusable codebase knowledge discovered during the work.
- `gotchas` contains pitfalls relevant to later iterations or stories.
- `blocker` contains the reason the story cannot be implemented safely; otherwise leave it null.
