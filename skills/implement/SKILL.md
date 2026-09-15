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

## Final Response

Briefly report in JSON format:

```json
{
  "description": "what was implemented",
  "files": [
    "file1",
    "file2"
  ],
  "patterns": [
    "pattern1",
    "pattern2"
  ],
  "gotchas": [
    "gotcha1",
    "gotcha2"
  ],
  "blocker": "blocker descrption"
}
```

* **description** is a brief explanation what you have just implemented
* **files** is a list of all files you have changed
* **patterns** are knowledge points you have discovered during the work  (e.g., "this codebase uses X for Y")
* **gotchas** are all gotchas encountered during the work, that can occur in subsequent iterations and stories( (e.g., "don't forget to update Z when changing W")
* **blocker** (optional) If the requirements are contradictory, so you can't implement the story, write the reason to this section. Otherwise leave it empty.

Do not claim that the story passed or is complete. The Ralph orchestrator determines that after running the configured quality checks.
