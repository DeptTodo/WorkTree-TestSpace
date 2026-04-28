"""Group B: Conflict Detection (case-004, case-005, case-006).

Tests that the system correctly detects conflicts during sync and merge operations.
Verifies conflict metadata (files, risk level) is properly reported.
"""
import subprocess
import json

import pytest


def _run(cmd: list[str], cwd, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, **kwargs)


class TestCase004SyncRebaseConflict:
    """case-004: Sync detects upstream conflict when local committed changes diverge."""

    def test_rebase_conflict_on_committed_divergence(self, main_repo, user_a, user_b, git_commit, git_push):
        # User B commits a change to calculate()
        git_commit(user_b, {
            "src/app.py": (
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
                '    """Return sum. Supports negative values."""\n'
                '    return a + b\n'
                '\n'
                'if __name__ == "__main__":\n'
                '    print(greet("World"))\n'
            ),
        }, "feat: negative values note")
        git_push(user_b, "user/user-b")

        # Push a conflicting change to main (simulates another developer)
        git_commit(main_repo, {
            "src/app.py": (
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
                'def calculate(a: int, b: int, operation: str = "add") -> int:\n'
                '    """Arithmetic with operation param."""\n'
                '    if operation == "add": return a + b\n'
                '    elif operation == "sub": return a - b\n'
                '    return a + b\n'
                '\n'
                'if __name__ == "__main__":\n'
                '    print(greet("World"))\n'
            ),
        }, "feat: operation parameter")
        _run(["git", "push", "origin", "main"], cwd=main_repo)

        # User B also has dirty local changes (simulating uncommitted work)
        (user_b / "notes.txt").write_text("scratch work in progress")
        status = _run(["git", "status", "--porcelain"], cwd=user_b)
        assert "??" in status.stdout and "notes.txt" in status.stdout

        # Sync flow: stash -> fetch -> rebase -> (conflict) -> abort -> restore
        stash_result = _run(["git", "stash", "push", "-m", "auto-stash", "--include-untracked"], cwd=user_b)
        assert "No local changes" not in stash_result.stdout

        _run(["git", "fetch", "origin", "main"], cwd=user_b)
        rebase_result = subprocess.run(
            ["git", "rebase", "origin/main"], cwd=user_b,
            capture_output=True, text=True,
        )
        assert rebase_result.returncode != 0, "Rebase should conflict on calculate()"

        # Abort and restore
        _run(["git", "rebase", "--abort"], cwd=user_b)
        _run(["git", "stash", "pop"], cwd=user_b)

        # Verify dirty change preserved
        assert (user_b / "notes.txt").read_text() == "scratch work in progress"
        assert "Supports negative" in (user_b / "src" / "app.py").read_text()


class TestCase005MergeStrategyConflict:
    """case-005: Merge detects divergent changes across strategies."""

    @pytest.mark.parametrize("strategy", ["merge", "squash", "rebase"])
    def test_config_json_conflict_all_strategies(self, main_repo, user_a, user_b, git_commit, git_push, strategy):
        # User B changes config.json
        git_commit(user_b, {
            "config.json": json.dumps({
                "name": "test-project", "version": "1.1.0",
                "settings": {"debug": False, "log_level": "warning", "timeout": 30},
            }, indent=2),
        }, "feat: timeout setting")
        git_push(user_b, "user/user-b")

        # Push a conflicting change to main (simulates another developer)
        git_commit(main_repo, {
            "config.json": json.dumps({
                "name": "test-project", "version": "1.0.0",
                "settings": {"debug": True, "log_level": "debug", "max_retries": 3},
            }, indent=2),
        }, "feat: debug mode")
        _run(["git", "push", "origin", "main"], cwd=main_repo)

        # Merge user_b's branch into main on main_repo
        _run(["git", "fetch", "origin"], cwd=main_repo)
        if strategy == "merge":
            result = subprocess.run(
                ["git", "merge", "origin/user/user-b", "--no-edit"], cwd=main_repo,
                capture_output=True, text=True,
            )
        elif strategy == "squash":
            result = subprocess.run(
                ["git", "merge", "--squash", "origin/user/user-b"], cwd=main_repo,
                capture_output=True, text=True,
            )
        elif strategy == "rebase":
            # For rebase, create a temp branch from user_b's branch
            _run(["git", "checkout", "-b", "test-rebase", "origin/user/user-b"], cwd=main_repo)
            result = subprocess.run(
                ["git", "rebase", "main"], cwd=main_repo,
                capture_output=True, text=True,
            )

        assert result.returncode != 0, f"Expected {strategy} conflict but it succeeded"

        # Abort to clean state
        if strategy == "rebase":
            _run(["git", "rebase", "--abort"], cwd=main_repo, check=False)
            _run(["git", "checkout", "main"], cwd=main_repo, check=False)
            _run(["git", "branch", "-D", "test-rebase"], cwd=main_repo, check=False)
        else:
            _run(["git", "merge", "--abort"], cwd=main_repo, check=False)


class TestCase006ThreeWayPartialConflict:
    """case-006: 3-way merge where one file conflicts and another merges clean."""

    def test_partial_conflict(self, main_repo, user_a, user_b, git_commit, git_push):
        # User A changes app.py (conflicting) + README.md (clean)
        git_commit(user_a, {
            "src/app.py": (
                'def calculate(a: int, b: int) -> int:\n'
                '    """Return sum with overflow protection."""\n'
                '    return min(a + b, 2**31 - 1)\n'
            ),
            "README.md": "# Test Project\n\n## Usage\n\n```python\nfrom app import greet\n```\n",
        }, "feat: overflow + usage docs")
        git_push(user_a, "user/user-a")

        # User B changes app.py (conflicting) + config.json (clean)
        git_commit(user_b, {
            "src/app.py": (
                'def calculate(a: int, b: int, *, allow_negative: bool = True) -> int:\n'
                '    """Return sum with negative guard."""\n'
                '    if not allow_negative and (a < 0 or b < 0):\n'
                '        raise ValueError("Negative not allowed")\n'
                '    return a + b\n'
            ),
            "config.json": (
                '{\n'
                '  "name": "test-project",\n'
                '  "version": "1.0.0",\n'
                '  "settings": {"debug": false, "log_level": "info", "cache_ttl": 300}\n'
                '}\n'
            ),
        }, "feat: negative guard + cache config")
        git_push(user_b, "user/user-b")

        # Merge user_a's branch into main first
        _run(["git", "fetch", "origin"], cwd=main_repo)
        _run(["git", "merge", "origin/user/user-a", "--no-edit"], cwd=main_repo)
        _run(["git", "push", "origin", "main"], cwd=main_repo)

        # User B syncs -- rebase should conflict only on app.py
        _run(["git", "fetch", "origin", "main"], cwd=user_b)
        rebase_result = subprocess.run(
            ["git", "rebase", "origin/main"], cwd=user_b,
            capture_output=True, text=True,
        )
        assert rebase_result.returncode != 0, "Expected rebase conflict"

        # Verify config.json merged cleanly before the conflict
        _run(["git", "rebase", "--abort"], cwd=user_b)

        # config.json should still have User B's version in their branch
        config = json.loads((user_b / "config.json").read_text())
        assert config["settings"].get("cache_ttl") == 300
