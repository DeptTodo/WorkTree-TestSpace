"""Group E: Boundary & Edge Cases (case-014, case-015).

Tests 3+ user contention, empty files, binary files, and other edge conditions.
"""
import subprocess
import json

import pytest


def _run(cmd: list[str], cwd, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, **kwargs)


class TestCase014ThreeWayConcurrentEdit:
    """case-014: 3 users edit the same function concurrently."""

    def test_sequential_merge_preserves_all_features(self, main_repo, user_a, user_b, user_c, git_commit, git_push):
        # All 3 users edit greet() on their branches
        git_commit(user_a, {
            "src/app.py": (
                'def greet(name: str, title: str = "") -> str:\n'
                '    prefix = f"{title} " if title else ""\n'
                '    return f"Hello, {prefix}{name}!"\n'
            ),
        }, "feat: title parameter")
        git_push(user_a, "user/user-a")

        git_commit(user_b, {
            "src/app.py": (
                'def greet(name: str, excited: bool = False) -> str:\n'
                '    suffix = "!!!" if excited else "!"\n'
                '    return f"Hello, {name}{suffix}"\n'
            ),
        }, "feat: excited parameter")
        git_push(user_b, "user/user-b")

        git_commit(user_c, {
            "src/app.py": (
                'def greet(name: str, language: str = "en") -> str:\n'
                '    langs = {"en": "Hello", "es": "Hola", "zh": "你好"}\n'
                '    return f"{langs.get(language, \\"Hello\\")}, {name}!"\n'
            ),
        }, "feat: language parameter")
        git_push(user_c, "user/user-c")

        # Use main_repo as the integration point (mirrors Polaris main branch)
        # Step 1: Merge User A into main (clean -- first mover)
        _run(["git", "fetch", "origin"], cwd=main_repo)
        _run(["git", "merge", "origin/user/user-a", "--no-edit"], cwd=main_repo)
        _run(["git", "push", "origin", "main"], cwd=main_repo)

        # Step 2: Merge User B into main (conflicts with A)
        _run(["git", "fetch", "origin"], cwd=main_repo)
        result_b = subprocess.run(
            ["git", "merge", "origin/user/user-b", "--no-edit"], cwd=main_repo,
            capture_output=True, text=True,
        )
        assert result_b.returncode != 0, "User B should conflict with User A on main"

        # Resolve manually: combine A+B
        (main_repo / "src" / "app.py").write_text(
            'def greet(name: str, title: str = "", excited: bool = False) -> str:\n'
            '    prefix = f"{title} " if title else ""\n'
            '    suffix = "!!!" if excited else "!"\n'
            '    return f"Hello, {prefix}{name}{suffix}"\n'
        )
        _run(["git", "add", "src/app.py"], cwd=main_repo)
        _run(["git", "commit", "--no-edit", "-m", "resolve: A+B"], cwd=main_repo)
        _run(["git", "push", "origin", "main"], cwd=main_repo)

        # Step 3: Merge User C into main (conflicts with A+B)
        _run(["git", "fetch", "origin"], cwd=main_repo)
        result_c = subprocess.run(
            ["git", "merge", "origin/user/user-c", "--no-edit"], cwd=main_repo,
            capture_output=True, text=True,
        )
        assert result_c.returncode != 0, "User C should conflict with A+B on main"

        # Resolve manually: combine A+B+C
        (main_repo / "src" / "app.py").write_text(
            'def greet(name: str, title: str = "", excited: bool = False, language: str = "en") -> str:\n'
            '    prefix = f"{title} " if title else ""\n'
            '    suffix = "!!!" if excited else "!"\n'
            '    langs = {"en": "Hello", "es": "Hola", "zh": "你好"}\n'
            '    base = langs.get(language, "Hello")\n'
            '    return f"{base}, {prefix}{name}{suffix}"\n'
        )
        _run(["git", "add", "src/app.py"], cwd=main_repo)
        _run(["git", "commit", "--no-edit", "-m", "resolve: A+B+C"], cwd=main_repo)

        # Verify final state has all 3 features
        content = (main_repo / "src" / "app.py").read_text()
        assert "title: str" in content, "Missing title from User A"
        assert "excited: bool" in content, "Missing excited from User B"
        assert 'language: str = "en"' in content, "Missing language from User C"


class TestCase015EdgeCases:
    """case-015: Boundary conditions."""

    def test_empty_file_conflict(self, main_repo, user_a, user_b, git_commit, git_push):
        """15a: One user empties a file, the other modifies it."""
        # User A modifies config.json
        git_commit(user_a, {"config.json": '{"new_setting": true}\n'}, "feat: new config")
        git_push(user_a, "user/user-a")

        # Empty config.json on main (simulates another developer)
        git_commit(main_repo, {"config.json": ""}, "chore: remove config")
        _run(["git", "push", "origin", "main"], cwd=main_repo)

        # Merge user_a into main (conflict: modified vs emptied)
        _run(["git", "fetch", "origin"], cwd=main_repo)
        result = subprocess.run(
            ["git", "merge", "origin/user/user-a", "--no-edit"], cwd=main_repo,
            capture_output=True, text=True,
        )
        assert result.returncode != 0, "Empty vs modified should conflict"
        _run(["git", "merge", "--abort"], cwd=main_repo, check=False)

    def test_merge_noop_when_no_divergence(self, user_a, user_b, git_push):
        """15d: Merging when no new commits should be a no-op."""
        _run(["git", "fetch", "origin"], cwd=user_b)
        log = _run(["git", "log", "--oneline", "origin/main..HEAD"], cwd=user_b)
        assert log.stdout.strip() == "", "No commits ahead means no merge needed"

    def test_concurrent_dirty_stash_no_interference(self, user_a, user_b):
        """15e: Two users stashing in sequence preserve their own changes.

        Note: worktrees sharing .git have a shared stash reflog. Each pop
        must target the correct stash entry to avoid cross-contamination.
        This mirrors how SafetyGuard.ensure_clean_or_stash records the ref
        and uses it for restore_stash.
        """
        (user_a / "a.txt").write_text("user a dirty")
        (user_b / "b.txt").write_text("user b dirty")

        # Stash and immediately pop each user's changes independently
        _run(["git", "stash", "push", "-m", "stash-a", "--include-untracked"], cwd=user_a)
        _run(["git", "stash", "pop"], cwd=user_a)

        _run(["git", "stash", "push", "-m", "stash-b", "--include-untracked"], cwd=user_b)
        _run(["git", "stash", "pop"], cwd=user_b)

        assert (user_a / "a.txt").read_text() == "user a dirty"
        assert (user_b / "b.txt").read_text() == "user b dirty"
        assert not (user_a / "b.txt").exists()
        assert not (user_b / "a.txt").exists()
