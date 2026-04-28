"""Group C: Conflict Resolution (case-007, case-008, case-009, case-010).

Tests the three resolution strategies (ours, theirs, manual) and multi-file
batch resolution. When the /resolve API endpoint is available, these tests
should be updated to call it. For now, they test the git-level resolution.
"""
import subprocess

import pytest


def _run(cmd: list[str], cwd, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, **kwargs)


def _setup_conflict(user_a, user_b, git_commit, git_push):
    """Create a conflict state on user_a by merging user_b's divergent changes."""
    # User A: multilingual greet
    git_commit(user_a, {
        "src/app.py": (
            'def greet(name: str, lang: str = "en") -> str:\n'
            '    """Multilingual greeting."""\n'
            '    greetings = {"en": f"Hello, {name}!", "zh": f"你好，{name}！"}\n'
            '    return greetings.get(lang, f"Hello, {name}!")\n'
        ),
    }, "feat: multilingual")
    git_push(user_a, "user/user-a")

    # User B: uppercase greet
    git_commit(user_b, {
        "src/app.py": (
            'def greet(name: str, uppercase: bool = False) -> str:\n'
            '    """Uppercase greeting option."""\n'
            '    msg = f"Hello, {name}!"\n'
            '    return msg.upper() if uppercase else msg\n'
        ),
    }, "feat: uppercase")
    git_push(user_b, "user/user-b")

    # Merge into user_a to create conflict
    _run(["git", "fetch", "origin"], cwd=user_a)
    _run(["git", "merge", "origin/main", "--no-edit"], cwd=user_a)
    result = subprocess.run(
        ["git", "merge", "origin/user/user-b", "--no-edit"], cwd=user_a,
        capture_output=True, text=True,
    )
    assert result.returncode != 0, "Expected conflict"
    return result


class TestCase007ResolveOurs:
    """case-007: Resolve conflict with 'ours' strategy."""

    def test_ours_keeps_our_version(self, user_a, user_b, git_commit, git_push):
        _setup_conflict(user_a, user_b, git_commit, git_push)

        # Resolve: keep ours
        _run(["git", "checkout", "--ours", "src/app.py"], cwd=user_a)
        _run(["git", "add", "src/app.py"], cwd=user_a)
        _run(["git", "commit", "--no-edit", "-m", "resolve: keep ours"], cwd=user_a)

        content = (user_a / "src" / "app.py").read_text()
        assert 'lang: str = "en"' in content, "Our version (multilingual) should be kept"
        assert "uppercase" not in content, "Their version should be discarded"
        assert "<<<<<<" not in content, "Conflict markers should be gone"


class TestCase008ResolveTheirs:
    """case-008: Resolve conflict with 'theirs' strategy."""

    def test_theirs_keeps_their_version(self, user_a, user_b, git_commit, git_push):
        _setup_conflict(user_a, user_b, git_commit, git_push)

        # Resolve: keep theirs
        _run(["git", "checkout", "--theirs", "src/app.py"], cwd=user_a)
        _run(["git", "add", "src/app.py"], cwd=user_a)
        _run(["git", "commit", "--no-edit", "-m", "resolve: keep theirs"], cwd=user_a)

        content = (user_a / "src" / "app.py").read_text()
        assert "uppercase" in content, "Their version (uppercase) should be kept"
        assert 'lang: str' not in content, "Our version should be discarded"


class TestCase009ResolveManual:
    """case-009: Manual resolution with user-provided content."""

    def test_manual_merges_both_features(self, user_a, user_b, git_commit, git_push):
        _setup_conflict(user_a, user_b, git_commit, git_push)

        # Write manual resolution combining both features
        merged = (
            'def greet(name: str, lang: str = "en", uppercase: bool = False) -> str:\n'
            '    """Greeting with language and case options."""\n'
            '    greetings = {"en": f"Hello, {name}!", "zh": f"你好，{name}！"}\n'
            '    msg = greetings.get(lang, f"Hello, {name}!")\n'
            '    return msg.upper() if uppercase else msg\n'
        )
        (user_a / "src" / "app.py").write_text(merged)
        _run(["git", "add", "src/app.py"], cwd=user_a)
        _run(["git", "commit", "--no-edit", "-m", "resolve: manual merge"], cwd=user_a)

        content = (user_a / "src" / "app.py").read_text()
        assert 'lang: str = "en"' in content, "Language param from ours"
        assert "uppercase: bool = False" in content, "Uppercase param from theirs"
        assert "<<<<<<" not in content


class TestCase010MultiFileBatchResolve:
    """case-010: Multi-file conflict resolved with different strategies per file."""

    def test_three_files_mixed_resolution(self, user_a, user_b, git_commit, git_push):
        # User A changes all 3 files
        git_commit(user_a, {
            "src/app.py": 'def greet(name: str, title: str = "") -> str:\n    return f"Hello, {title} {name}!"\n',
            "config.json": '{"debug": true, "log_level": "debug"}\n',
            "README.md": "# My Project v2\n",
        }, "feat: A's changes")
        git_push(user_a, "user/user-a")

        # User B changes same 3 files
        git_commit(user_b, {
            "src/app.py": 'def greet(name: str, excited: bool = False) -> str:\n    return f"Hello, {name}{"!!!" if excited else "!"}\n',
            "config.json": '{"debug": false, "cache": true}\n',
            "README.md": "# Test Project Production\n",
        }, "feat: B's changes")
        git_push(user_b, "user/user-b")

        # Merge to create 3-file conflict
        _run(["git", "fetch", "origin"], cwd=user_a)
        _run(["git", "merge", "origin/main", "--no-edit"], cwd=user_a)
        result = subprocess.run(
            ["git", "merge", "origin/user/user-b", "--no-edit"], cwd=user_a,
            capture_output=True, text=True,
        )
        assert result.returncode != 0

        # Resolve app.py with "ours"
        _run(["git", "checkout", "--ours", "src/app.py"], cwd=user_a)
        _run(["git", "add", "src/app.py"], cwd=user_a)

        # Resolve config.json with "theirs"
        _run(["git", "checkout", "--theirs", "config.json"], cwd=user_a)
        _run(["git", "add", "config.json"], cwd=user_a)

        # Resolve README.md manually
        (user_a / "README.md").write_text("# My Project v2 (Production)\n")
        _run(["git", "add", "README.md"], cwd=user_a)

        # Complete merge
        _run(["git", "commit", "--no-edit", "-m", "resolve: mixed strategies"], cwd=user_a)

        # Verify
        assert 'title: str' in (user_a / "src" / "app.py").read_text()
        assert '"cache": true' in (user_a / "config.json").read_text()
        assert "Production" in (user_a / "README.md").read_text()
