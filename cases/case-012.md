# case-012: Backup Branch Creation Before Merge

## Metadata

| Field | Value |
|-------|-------|
| ID | case-012 |
| Group | D -- Safety Net |
| Priority | P0 (loss prevention) |
| Conflict Expected | No (safety mechanism) |
| Spec Reference | Phase 2 -- SafetyGuard.snapshot_branch() |

## Scenario

Before any merge operation, the system creates a backup branch pointing to the
current HEAD. If the merge goes wrong (conflict, bad result), the user can rollback
to the exact pre-merge state via `restore_branch()`.

## Preconditions

- User worktree at `/tmp/wt-user-a` on branch `feat/user-a-task`
- Current HEAD at known SHA

## Steps

### Step 1: Record pre-merge SHA

```bash
PRE_SHA=$(git -C /tmp/wt-user-a rev-parse HEAD)
echo "Pre-merge SHA: $PRE_SHA"
```

### Step 2: Trigger merge (backup happens automatically)

```bash
POST /api/projects/{pid}/worktrees/{wid}/merge
{
  "targetBranch": "main",
  "strategy": "merge"
}
```

Internally `WorktreeMergeService.merge()`:
1. `SafetyGuard.snapshot_branch(cwd, branch_hint="merge-main")` -> `BackupRecord`
2. `git checkout main`
3. `git merge feat/user-a-task`
4. On conflict: `SafetyGuard.restore_branch(cwd, backup_record)`

### Step 3: Verify backup branch exists

```bash
git -C /tmp/wt-user-a branch --list 'backup/*'
# Expected: backup/merge-main-20260428-HHMMSS
```

### Step 4: Verify backup points to pre-merge SHA

```bash
BACKUP_BRANCH=$(git -C /tmp/wt-user-a branch --list 'backup/*' | head -1 | tr -d ' ')
BACKUP_SHA=$(git -C /tmp/wt-user-a rev-parse "$BACKUP_BRANCH")
echo "Backup SHA: $BACKUP_SHA"

# Compare
[ "$PRE_SHA" = "$BACKUP_SHA" ] && echo "PASS: SHAs match" || echo "FAIL: SHAs differ"
```

## Expected Results

| Check | Expected |
|-------|----------|
| Backup branch created | Yes, name matches `backup/<hint>-<timestamp>` |
| Backup SHA == pre-merge SHA | Exact match |
| Backup branch is a regular ref | Yes (not a tag, not detached) |
| Audit log | `merge` operation detail includes `backup_branch` name |
| Domain event | `WorktreeMerged` includes `backup_branch` field |

## Rollback Verification

```bash
# If merge produced bad result, rollback to backup
POST /api/projects/{pid}/worktrees/{wid}/rollback

# Verify HEAD is back to pre-merge SHA
git -C /tmp/wt-user-a rev-parse HEAD
# Expected: matches $PRE_SHA
```

## Automation

- **pytest**: `automation/pytest/test_safety_net.py::test_backup_branch_created`
- **pytest**: `automation/pytest/test_safety_net.py::test_rollback_to_backup`
- **Playwright**: Merge dialog shows "Backup: backup/merge-main-*" info text
