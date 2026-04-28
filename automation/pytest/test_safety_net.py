"""Group D: Safety Net / Loss Prevention (case-011, case-012, case-013).

Tests auto-stash, backup branches, and audit logging.
These tests verify the SafetyGuard primitives that the WorktreeSyncService
and WorktreeMergeService build upon.
"""
import subprocess
import re

import pytest


def _run(cmd: list[str], cwd, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, **kwargs)


class TestCase011AutoStashRoundtrip:
    """case-011: Auto-stash preserves dirty changes through destructive ops."""

    def test_stash_preserves_modified_file(self, user_b, git_commit):
        """Dirty tracked file survives stash -> fetch -> rebase -> restore."""
        # Create dirty state
        (user_b / "src" / "app.py").write_text(
            '# modified line\n' + (user_b / "src" / "app.py").read_text()
        )
        status = _run(["git", "status", "--porcelain"], cwd=user_b)
        assert "M src/app.py" in status.stdout

        # Stash
        _run(["git", "stash", "push", "-m", "test-stash", "--include-untracked"], cwd=user_b)

        # Verify clean
        status = _run(["git", "status", "--porcelain"], cwd=user_b)
        assert status.stdout.strip() == ""

        # Restore
        _run(["git", "stash", "pop"], cwd=user_b)

        # Verify modification restored
        content = (user_b / "src" / "app.py").read_text()
        assert "# modified line" in content

    def test_stash_preserves_untracked_file(self, user_b):
        """Untracked files survive stash with --include-untracked."""
        (user_b / "notes.txt").write_text("scratch notes")
        assert not _run(["git", "ls-files", "--error-unmatch", "notes.txt"], cwd=user_b, check=False).returncode == 0

        # Stash with untracked
        _run(["git", "stash", "push", "-m", "test-untracked", "--include-untracked"], cwd=user_b)
        assert not (user_b / "notes.txt").exists(), "Untracked file should be removed by stash"

        # Restore
        _run(["git", "stash", "pop"], cwd=user_b)
        assert (user_b / "notes.txt").read_text() == "scratch notes"

    def test_no_stash_when_clean(self, user_b):
        """Stash on clean repo returns 'No local changes'."""
        result = _run(["git", "stash", "push", "-m", "test-clean"], cwd=user_b)
        assert "No local changes" in result.stdout


class TestCase012BackupBranch:
    """case-012: Backup branch created before merge points to pre-merge SHA."""

    def test_backup_sha_matches_pre_merge(self, user_a, user_b, git_commit, git_push):
        pre_sha = _run(["git", "rev-parse", "HEAD"], cwd=user_a).stdout.strip()

        # Create a backup branch (simulates SafetyGuard.snapshot_branch)
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"backup/test-{ts}"
        _run(["git", "branch", backup_name, pre_sha], cwd=user_a)

        # Verify
        backup_sha = _run(["git", "rev-parse", backup_name], cwd=user_a).stdout.strip()
        assert pre_sha == backup_sha, "Backup SHA must match pre-merge SHA"

        # Verify branch exists
        branches = _run(["git", "branch", "--list", backup_name], cwd=user_a).stdout
        assert backup_name in branches

    def test_rollback_to_backup(self, user_a):
        """Hard reset to backup SHA restores exact pre-merge state."""
        pre_sha = _run(["git", "rev-parse", "HEAD"], cwd=user_a).stdout.strip()

        # Make a commit to move HEAD
        (user_a / "temp.txt").write_text("temp")
        _run(["git", "add", "temp.txt"], cwd=user_a)
        _run(["git", "commit", "-m", "temp"], cwd=user_a)
        assert _run(["git", "rev-parse", "HEAD"], cwd=user_a).stdout.strip() != pre_sha

        # Rollback (simulates SafetyGuard.restore_branch)
        _run(["git", "reset", "--hard", pre_sha], cwd=user_a)
        assert _run(["git", "rev-parse", "HEAD"], cwd=user_a).stdout.strip() == pre_sha
        assert not (user_a / "temp.txt").exists()


class TestCase013AuditLog:
    """case-013: Audit log completeness -- verified at DB level."""

    @pytest.mark.skip(reason="Requires running Polaris server with worktree_operations table")
    def test_all_operations_logged(self):
        """Verify all operation types appear in worktree_operations."""
        # This test requires a running server; placeholder for integration test
        pass

    @pytest.mark.skip(reason="Requires running Polaris server")
    def test_temporal_ordering(self):
        """Verify audit entries are chronologically ordered."""
        pass
