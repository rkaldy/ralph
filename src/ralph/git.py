import subprocess
from pathlib import Path

from ralph import ui
from ralph.exceptions import RalphError


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip() or "Unknown Git error"
        raise RalphError(f"Git command failed: {output}")
    return result


def prepare_branch(branch_name: str) -> None:
    run_git("check-ref-format", "--branch", branch_name)

    current_branch = run_git("branch", "--show-current").stdout.strip()
    if current_branch == branch_name:
        return

    branch = run_git("show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}", check=False)
    if branch.returncode == 0:
        run_git("switch", "--", branch_name)
    elif branch.returncode == 1:
        run_git("switch", "-c", branch_name)
    else:
        output = branch.stderr.strip() or branch.stdout.strip() or "Could not inspect Git branch"
        raise RalphError(f"Git command failed: {output}")


def commit_story(story_title: str) -> None:
    run_git("add", "--all")
    staged_changes = run_git("diff", "--cached", "--quiet", check=False)
    if staged_changes.returncode == 0:
        ui.console.print("No changes to commit\n", style="meta")
        return
    if staged_changes.returncode != 1:
        output = (
            staged_changes.stderr.strip() or staged_changes.stdout.strip() or "Could not inspect staged changes"
        )
        raise RalphError(f"Git command failed: {output}")

    run_git("commit", "-m", story_title)
