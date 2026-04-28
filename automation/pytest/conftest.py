"""Shared fixtures for WorkTree management tests.

Uses real git worktree (not clone) to match Polaris production architecture.
Each user gets a worktree at <project>/.claude/worktrees/<username>/ on branch
user/<username>, sharing the same .git directory with the main repo.

Layout:
    tmp_path/
    ├── origin.git/                  ← bare remote
    ├── project/                     ← main repo (clone of origin)
    │   ├── src/app.py, README.md, config.json
    │   └── .claude/worktrees/
    │       ├── user-a/             ← git worktree add -b user/user-a
    │       ├── user-b/             ← git worktree add -b user/user-b
    │       └── user-c/             ← git worktree add -b user/user-c
"""
import subprocess
import shutil
from pathlib import Path

import pytest


def _run(cmd: list[str], cwd: Path, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a command, raise on failure by default."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, **kwargs)


def _seed_repo(repo_dir: Path) -> None:
    """Seed a git repo with initial content matching fixtures/shared-repo.md."""
    _run(["git", "config", "user.email", "test@fixture"], cwd=repo_dir)
    _run(["git", "config", "user.name", "TestFixture"], cwd=repo_dir)

    (repo_dir / "src").mkdir(exist_ok=True)
    (repo_dir / "src" / "app.py").write_text(
        '"""Main application module."""\n'
        '\n'
        'VERSION = "1.0.0"\n'
        '\n'
        'def greet(name: str) -> str:\n'
        '    """Return a greeting message."""\n'
        '    return f"Hello, {name}!"\n'
        '\n'
        'def farewell(name: str) -> str:\n'
        '    """Return a farewell message."""\n'
        '    return f"Goodbye, {name}!"\n'
        '\n'
        'def calculate(a: int, b: int) -> int:\n'
        '    """Return sum of two numbers."""\n'
        '    return a + b\n'
        '\n'
        'if __name__ == "__main__":\n'
        '    print(greet("World"))\n'
    )
    (repo_dir / "README.md").write_text(
        "# Test Project\n\n"
        "A sample project for worktree testing.\n\n"
        "## Features\n- Greeting\n- Farewell\n- Calculator\n"
    )
    (repo_dir / "config.json").write_text(
        '{\n'
        '  "name": "test-project",\n'
        '  "version": "1.0.0",\n'
        '  "settings": {\n'
        '    "debug": false,\n'
        '    "log_level": "info"\n'
        '  }\n'
        '}\n'
    )
    _run(["git", "add", "."], cwd=repo_dir)
    _run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir)


@pytest.fixture
def origin(tmp_path):
    """Create a bare origin repo seeded with initial content."""
    origin_dir = tmp_path / "origin.git"
    origin_dir.mkdir()
    _run(["git", "init", "--bare", "--initial-branch=main", str(origin_dir)], cwd=tmp_path)

    # Use a temp working copy to push initial content
    seed_dir = tmp_path / "seed"
    _run(["git", "clone", str(origin_dir), str(seed_dir)], cwd=tmp_path)
    _seed_repo(seed_dir)
    _run(["git", "push", "-u", "origin", "main"], cwd=seed_dir)
    shutil.rmtree(seed_dir)

    return origin_dir


@pytest.fixture
def main_repo(origin, tmp_path):
    """Main project repo — the Polaris 'project_cwd'.

    Acts as the parent for git worktrees. Users who need to operate directly
    on main (e.g., pushing conflicting changes to simulate other developers)
    should use this fixture.
    """
    project = tmp_path / "project"
    _run(["git", "clone", str(origin), str(project)], cwd=tmp_path)
    _run(["git", "config", "user.email", "main@test"], cwd=project)
    _run(["git", "config", "user.name", "MainRepo"], cwd=project)
    # Create the .claude/worktrees directory structure (mirrors Polaris)
    (project / ".claude" / "worktrees").mkdir(parents=True)
    return project


def _create_worktree(main_repo: Path, username: str, branch: str) -> Path:
    """Create a git worktree under .claude/worktrees/<username>/."""
    wt_path = main_repo / ".claude" / "worktrees" / username
    _run(
        ["git", "worktree", "add", "-b", branch, str(wt_path)],
        cwd=main_repo,
    )
    _run(["git", "config", "user.email", f"{username}@test"], cwd=wt_path)
    _run(["git", "config", "user.name", username.capitalize()], cwd=wt_path)
    return wt_path


@pytest.fixture
def user_a(main_repo):
    """User A worktree on branch user/user-a."""
    return _create_worktree(main_repo, "user-a", "user/user-a")


@pytest.fixture
def user_b(main_repo):
    """User B worktree on branch user/user-b."""
    return _create_worktree(main_repo, "user-b", "user/user-b")


@pytest.fixture
def user_c(main_repo):
    """User C worktree on branch user/user-c."""
    return _create_worktree(main_repo, "user-c", "user/user-c")


@pytest.fixture
def git_commit():
    """Helper to commit changes in a worktree."""

    def _commit(wt: Path, files: dict[str, str], message: str):
        for relpath, content in files.items():
            fpath = wt / relpath
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content)
        _run(["git", "add", "."], cwd=wt)
        _run(["git", "commit", "-m", message], cwd=wt)

    return _commit


@pytest.fixture
def git_push():
    """Helper to push a branch to origin.

    Works from any worktree since all share the same .git.
    """

    def _push(wt: Path, branch: str | None = None):
        cmd = ["git", "push", "origin"]
        if branch:
            cmd.append(branch)
        else:
            cmd.append("--all")
        _run(cmd, cwd=wt)

    return _push
