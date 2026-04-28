"""Shared fixtures for WorkTree management tests.

Creates isolated git repos per test to avoid cross-test contamination.
Each fixture is a temporary directory with a bare origin + working clones.
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
def user_a(origin, tmp_path):
    """User A worktree, branch feat/user-a-task."""
    wt = tmp_path / "user-a"
    _run(["git", "clone", str(origin), str(wt)], cwd=tmp_path)
    _run(["git", "config", "user.email", "user-a@test"], cwd=wt)
    _run(["git", "config", "user.name", "UserA"], cwd=wt)
    _run(["git", "checkout", "-b", "feat/user-a-task"], cwd=wt)
    return wt


@pytest.fixture
def user_b(origin, tmp_path):
    """User B worktree, branch feat/user-b-task."""
    wt = tmp_path / "user-b"
    _run(["git", "clone", str(origin), str(wt)], cwd=tmp_path)
    _run(["git", "config", "user.email", "user-b@test"], cwd=wt)
    _run(["git", "config", "user.name", "UserB"], cwd=wt)
    _run(["git", "checkout", "-b", "feat/user-b-task"], cwd=wt)
    return wt


@pytest.fixture
def user_c(origin, tmp_path):
    """User C worktree, branch feat/user-c-task (for 3+ user tests)."""
    wt = tmp_path / "user-c"
    _run(["git", "clone", str(origin), str(wt)], cwd=tmp_path)
    _run(["git", "config", "user.email", "user-c@test"], cwd=wt)
    _run(["git", "config", "user.name", "UserC"], cwd=wt)
    _run(["git", "checkout", "-b", "feat/user-c-task"], cwd=wt)
    return wt


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
    """Helper to push a branch to origin."""

    def _push(wt: Path, branch: str | None = None):
        cmd = ["git", "push", "origin"]
        if branch:
            cmd.append(branch)
        else:
            cmd.append("--all")
        _run(cmd, cwd=wt)

    return _push
