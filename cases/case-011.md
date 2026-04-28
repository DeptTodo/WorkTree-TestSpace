# case-011: Auto-Stash on Dirty Worktree Before Destructive Op

## Metadata

| Field | Value |
|-------|-------|
| ID | case-011 |
| Group | D -- Safety Net |
| Priority | P0 (loss prevention) |
| Conflict Expected | No |
| Spec Reference | Phase 2 -- SafetyGuard.stash_backup(), Phase 6 -- polaris-git-guard.sh Hook |

## Scenario

User has uncommitted changes in their worktree. A destructive operation (sync, merge,
or `git reset --hard` via Claude) is about to execute. The system MUST auto-stash
dirty changes BEFORE the operation, and restore them AFTER. Zero data loss.

## Preconditions

- User worktree at `/tmp/wt-user-a` with uncommitted changes to `src/app.py`
- New untracked file `notes.txt` in worktree root

## Steps

### Step 1: Create dirty state

```bash
cd /tmp/wt-user-a

# Modify tracked file
echo "# modified line" >> src/app.py

# Add untracked file
echo "scratch notes" > notes.txt

# Verify dirty
git status --porcelain
# Expected:
#  M src/app.py
# ?? notes.txt
```

### Step 2: Call sync() (triggers auto-stash)

```bash
POST /api/projects/{pid}/worktrees/{wid}/sync
```

Internally `WorktreeSyncService.sync()`:
1. `SafetyGuard.stash_backup(cwd)` -- stash includes `--include-untracked`
2. `git fetch origin main`
3. `git rebase origin/main`
4. `SafetyGuard.restore_stash(cwd, record)`

### Step 3: Verify recovery

```bash
# Check modified file is restored
git -C /tmp/wt-user-a diff src/app.py
# Expected: shows "# modified line" addition

# Check untracked file is restored
cat /tmp/wt-user-a/notes.txt
# Expected: "scratch notes"

# Check stash list is clean (stash was popped)
git -C /tmp/wt-user-a stash list
# Expected: empty
```

## Expected Results

| Check | Expected |
|-------|----------|
| Modified file preserved | `src/app.py` still has "# modified line" |
| Untracked file preserved | `notes.txt` exists with "scratch notes" |
| Stash created | `polaris-auto-stash-*` message in stash |
| Stash popped | `git stash list` empty after sync |
| Sync result | `success` or `conflict` (either is fine, data must not be lost) |
| Audit log | `stash` operation logged, `restore` operation logged |

## Hook Verification (polaris-git-guard.sh)

```bash
# Simulate Claude running "git reset --hard" on dirty worktree
echo '{"tool_input":{"command":"git reset --hard"},"cwd":"/tmp/wt-user-a"}' \
  | bash scripts/hooks/polaris-git-guard.sh

# Verify auto-stash happened
git -C /tmp/wt-user-a stash list
# Expected: contains "polaris-guard-stash-*"

# Verify dirty changes still recoverable
git -C /tmp/wt-user-a stash pop
cat /tmp/wt-user-a/notes.txt
# Expected: "scratch notes"
```

## Failure Modes

| Failure | Behavior | Data Loss? |
|---------|----------|------------|
| Stash push fails | Raise exception, abort sync | No (operation never starts) |
| Stash pop conflicts | Return `SyncResult(status='conflict')` with stash files | No (stash still exists) |
| Hook script crashes | fail-open (exit 0), log to `hook.log` | Possible (hook is best-effort) |
| Git timeout (60s) | `asyncio.TimeoutError` raised | No (stash created before timeout) |

## Automation

- **pytest**: `automation/pytest/test_safety_net.py::test_auto_stash_roundtrip`
- **pytest**: `automation/pytest/test_safety_net.py::test_untracked_file_preserved`
- **Playwright**: Verify "Syncing" state shows stash indicator in UI
