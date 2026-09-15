---
name: execute
description: Implement one user story selected by the Ralph orchestrator from the workspace's `prd.json`.
---

# Ralph Story Implementation

Implement the single user story identified in the current prompt. Keep the change focused on that story and its acceptance criteria.

## Context

- Follow all applicable `AGENTS.md` instructions in the workspace.
- Read the selected story in `prd.json` for its complete requirements and acceptance criteria.
- Read all the **Codebase Patterns** and **Gotchas encountered** sections in `progress.md`, if the file exists, before making changes.
- Inspect the relevant code and follow established project patterns.

If the requested story cannot be found or its requirements are contradictory, report the blocker instead of selecting or implementing a different story.

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
- Make any changes in `prd.json` or `progress.md`
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
