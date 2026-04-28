"""Group A: Parallel Edit Scenarios (case-001, case-002, case-003).

Tests multi-user concurrent file editing and merge outcomes.
These tests use raw git operations to verify the underlying merge behavior
that WorktreeMergeService relies on.

When the WorktreeMergeService is implemented, these should be updated to
call the service API instead of raw git commands.
"""
import subprocess

import pytest


def _run(cmd: list[str], cwd, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, **kwargs)


def _merge_branch(wt, source_branch: str) -> subprocess.CompletedProcess:
    """Merge source_branch into current branch. Returns result (may fail)."""
    return subprocess.run(
        ["git", "merge", source_branch, "--no-edit"],
        cwd=wt, capture_output=True, text=True,
    )


class TestCase001DifferentPartsNoConflict:
    """case-001: Two worktrees edit different parts of the same file."""

    def test_greet_and_farewell_merge_cleanly(self, user_a, user_b, git_commit, git_push):
        # User A edits greet() (top of file)
        git_commit(user_a, {
            "src/app.py": (
                '"""Main application module."""\n'
                '\n'
                'VERSION = "1.0.0"\n'
                '\n'
                'def greet(name: str) -> str:\n'
                '    """Return a personalized greeting message."""\n'
                '    return f"Hello, {name}! Welcome to our project."\n'
                '\n'
                'def farewell(name: str) -> str:\n'
                '    """Return a farewell message."""\n'
                '    return f"Goodbye, {name}!"\n'
                '\n'
                'def calculate(a: int, b: int) -> int:\n'
                '    """Return sum of two numbers."""\n'
                '    return a + b\n'
            ),
        }, "feat: personalize greeting")
        git_push(user_a, "user/user-a")

        # User B edits farewell() (middle of file)
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
                '    """Return a warm farewell message."""\n'
                '    return f"Goodbye, {name}! See you next time."\n'
                '\n'
                'def calculate(a: int, b: int) -> int:\n'
                '    """Return sum of two numbers."""\n'
                '    return a + b\n'
            ),
        }, "feat: warm farewell")
        git_push(user_b, "user/user-b")

        # User A merges main + User B's branch
        _run(["git", "fetch", "origin"], cwd=user_a)
        _run(["git", "merge", "origin/main", "--no-edit"], cwd=user_a)
        result = _merge_branch(user_a, "origin/user/user-b")

        assert result.returncode == 0, f"Merge failed: {result.stderr}"
        content = (user_a / "src/app.py").read_text()
        assert "Welcome to our project" in content, "User A's greet change missing"
        assert "See you next time" in content, "User B's farewell change missing"

    def test_different_files_no_conflict(self, user_a, user_b, git_commit, git_push):
        """case-003: Two worktrees edit different files."""
        # User A edits app.py
        git_commit(user_a, {
            "src/app.py": (
                'def multiply(a: int, b: int) -> int:\n'
                '    """Return product."""\n'
                '    return a * b\n'
            ),
        }, "feat: add multiply")
        git_push(user_a, "user/user-a")

        # User B edits README.md
        git_commit(user_b, {
            "README.md": "# Test Project\n\n## Installation\n\n```bash\npip install test-project\n```\n",
        }, "docs: add installation")
        git_push(user_b, "user/user-b")

        # Merge both into user_a
        _run(["git", "fetch", "origin"], cwd=user_a)
        _run(["git", "merge", "origin/main", "--no-edit"], cwd=user_a)
        result = _merge_branch(user_a, "origin/user/user-b")

        assert result.returncode == 0, f"Merge failed: {result.stderr}"
        assert "multiply" in (user_a / "src/app.py").read_text()
        assert "Installation" in (user_a / "README.md").read_text()


class TestCase002SamePartConflict:
    """case-002: Two worktrees edit the same part of the same file -- MUST conflict."""

    def test_same_function_signature_conflicts(self, user_a, user_b, git_commit, git_push):
        # User A changes greet() signature
        git_commit(user_a, {
            "src/app.py": (
                'def greet(name: str, lang: str = "en") -> str:\n'
                '    """Return a greeting in specified language."""\n'
                '    greetings = {"en": f"Hello, {name}!", "zh": f"你好，{name}！"}\n'
                '    return greetings.get(lang, f"Hello, {name}!")\n'
            ),
        }, "feat: multilingual greeting")
        git_push(user_a, "user/user-a")

        # User B changes greet() signature differently
        git_commit(user_b, {
            "src/app.py": (
                'def greet(name: str, uppercase: bool = False) -> str:\n'
                '    """Return a greeting, optionally uppercased."""\n'
                '    msg = f"Hello, {name}!"\n'
                '    return msg.upper() if uppercase else msg\n'
            ),
        }, "feat: uppercase greeting")
        git_push(user_b, "user/user-b")

        # Merge should conflict
        _run(["git", "fetch", "origin"], cwd=user_a)
        _run(["git", "merge", "origin/main", "--no-edit"], cwd=user_a)
        result = _merge_branch(user_a, "origin/user/user-b")

        assert result.returncode != 0, "Expected merge conflict but it succeeded"
        assert "CONFLICT" in result.stdout or "CONFLICT" in result.stderr

        # Abort merge to clean state
        _run(["git", "merge", "--abort"], cwd=user_a)
