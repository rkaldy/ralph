---
name: "program"
description: "Implement or repair one Ralph user story selected by the orchestrator from `.ralph/prd.json`, including follow-up iterations for lint, typecheck, or test failures."
---

# Ralph Story Implementation

Code the single user story identified in the current prompt. Keep the change focused on that story and its acceptance criteria.

## Context

- Follow all applicable `AGENTS.md` instructions in the workspace.
- Read all the **Codebase Patterns** and **Gotchas encountered** sections in `.ralph/progress.md`, if the file exists, before making changes.
- Inspect the relevant code and follow established project patterns.
- Use the original PRD only for global requirements, non-goals, technical constraints, terminology, and dependencies relevant to the selected story.
- Other stories in the original PRD are context, not additional implementation scope.

If the requirements are valid, and you are able to implement it, write a final response with exact text:
```text
<COMPLETE>
```

If the requirements are contradictory, or there are other reason why you are unable to implement it, write a final response with a brief explanation why you can't implement the story.  

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
