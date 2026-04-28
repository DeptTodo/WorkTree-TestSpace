# case-004: Sync Detects Upstream Conflict (Rebase Path)

## Metadata

| Field | Value |
|-------|-------|
| ID | case-004 |
| Group | B -- Conflict Detection |
| Priority | P0 |
| Conflict Expected | **Yes (rebase conflict during sync)** |
| Spec Reference | Phase 3 -- WorktreeSyncService `sync()` |

## Scenario

User B has local uncommitted + committed changes to `src/app.py`. Meanwhile User A
pushes conflicting changes to `origin/main`. When User B calls `sync()`, the rebase
step detects the conflict. The sync service must: abort rebase, restore stash (if any),
return `SyncResult(status='conflict')`.

## Preconditions

- Standard shared fixture
- User A worktree at `/tmp/wt-user-a` (drives upstream changes)
- User B worktree at `/tmp/wt-user-b` (has dirty local changes)

## Steps

### Step 1: User B makes dirty local changes (uncommitted)

```bash
cd /tmp/wt-user-b
```

Edit `src/app.py` -- modify `calculate()`:

```python
def calculate(a: int, b: int) -> int:
    """Return sum of two numbers. Supports negative values."""
    return a + b
```

**Do NOT commit or stash** -- leave dirty.

### Step 2: User A pushes conflicting change to `main`

```bash
cd /tmp/wt-user-a
git checkout main
```

Edit `src/app.py` -- modify `calculate()` differently:

```python
def calculate(a: int, b: int, operation: str = "add") -> int:
    """Return result of arithmetic operation."""
    if operation == "add":
        return a + b
    elif operation == "sub":
        return a - b
    return a + b
```

```bash
git add src/app.py
git commit -m "feat: add operation parameter to calculate"
git push origin main
```

### Step 3: User B calls sync()

```bash
POST /api/projects/{pid}/worktrees/{wid}/sync
```

Internally, `WorktreeSyncService.sync()`:
1. Detects dirty state -> auto-stash (stash has B's `calculate()` change)
2. `git fetch origin main`
3. `git rebase origin/main` -- CONFLICT on `src/app.py`
4. `git rebase --abort`
5. Restore stash (B's dirty change comes back)
6. Return `SyncResult(status='conflict')`

## Expected Results

| Check | Expected |
|-------|----------|
| Sync result status | `conflict` |
| `conflict_files` | `["src/app.py"]` |
| `had_stash` | `true` (auto-stashed before rebase) |
| User B's dirty change preserved | Yes (stash restored after rebase abort) |
| Rebase aborted | Yes (no partial rebase state) |
| `WorktreeConflict` event | Emitted with `operation="sync"` |
| Audit log | `sync` with `status=failed` |
| Stash list contains auto-stash | `git stash list` shows `polaris-auto-stash-*` |

## Verification Commands

```bash
# Verify User B's dirty change is preserved
git -C /tmp/wt-user-b diff src/app.py
# Expected: shows B's "Supports negative values" change

# Verify no rebase in progress
git -C /tmp/wt-user-b status
# Expected: no "rebase in progress" message

# Verify stash was used and restored
git -C /tmp/wt-user-b stash list
# Expected: empty (stash was popped after rebase abort)

# Verify conflict event via WebSocket (if connected)
# Expected message: {"type":"ctrl","event":"worktree:conflict-detected","data":{...}}
```

## Failure Mode Matrix

| Failure | Expected Behavior | Spec Reference |
|---------|-------------------|----------------|
| Stash pop conflicts after rebase abort | Return `status='conflict'` with stash conflict files | SyncService L880-886 |
| Rebase abort fails | Last-resort stash restore attempt, then raise | SyncService L892-898 |
| Git fetch timeout | Raise exception, try stash restore | SafetyGuard timeout=60 |

## Automation

- **pytest**: `automation/pytest/test_conflict_detection.py::test_sync_rebase_conflict`
- **Playwright**:
  1. Verify "Needs Sync" badge on card before sync
  2. Click sync button, verify conflict dialog appears
  3. Screenshot conflict state showing preserved local changes
