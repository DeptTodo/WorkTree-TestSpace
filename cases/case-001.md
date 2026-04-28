# case-001: Two Worktrees Edit Different Parts of Same File

## Metadata

| Field | Value |
|-------|-------|
| ID | case-001 |
| Group | A -- Parallel Edit |
| Priority | P0 (critical path) |
| Conflict Expected | No (clean merge) |
| Spec Reference | Phase 3 -- WorktreeSyncService, WorktreeMergeService |

## Scenario

User A and User B both work on `src/app.py`. User A modifies the `greet()` function
(top of file), User B modifies the `farewell()` function (middle of file).
Their changes do not overlap -- merge should succeed without conflict.

## Preconditions

- Shared origin repo at `/tmp/wt-test-origin.git` with `main` branch (see `fixtures/shared-repo.md`)
- User A worktree at `/tmp/wt-user-a` on branch `feat/user-a-task`
- User B worktree at `/tmp/wt-user-b` on branch `feat/user-b-task`
- Both branches are up-to-date with `origin/main`

## Steps

### Step 1: User A edits `greet()` function

```bash
cd /tmp/wt-user-a
```

Edit `src/app.py` -- change `greet()` only (lines 6-8):

```python
def greet(name: str) -> str:
    """Return a personalized greeting message."""
    return f"Hello, {name}! Welcome to our project."
```

```bash
git add src/app.py
git commit -m "feat: personalize greeting message"
git push origin feat/user-a-task
```

### Step 2: User B edits `farewell()` function

```bash
cd /tmp/wt-user-b
```

Edit `src/app.py` -- change `farewell()` only (lines 10-12):

```python
def farewell(name: str) -> str:
    """Return a warm farewell message."""
    return f"Goodbye, {name}! See you next time."
```

```bash
git add src/app.py
git commit -m "feat: warm farewell message"
git push origin feat/user-b-task
```

### Step 3: User A merges User B's changes (via WorktreeMergeService)

```bash
# API call (or via WorktreeManagementService.merge)
POST /api/projects/{pid}/worktrees/{wid}/merge
{
  "targetBranch": "main",
  "strategy": "merge"
}
```

### Step 4: User B syncs (via WorktreeSyncService)

```bash
# API call
POST /api/projects/{pid}/worktrees/{wid}/sync
```

## Expected Results

| Check | Expected |
|-------|----------|
| Merge status | `success` (no conflict) |
| `conflict_files` | `[]` (empty) |
| `src/app.py` contains both changes | `greet()` has "Welcome to our project", `farewell()` has "See you next time" |
| Backup branch created | Yes (e.g., `backup/merge-main-20260428-*`) |
| Audit log entries | `merge` operation with `status=success` |
| User B sync result | `success`, pulls merged changes |

## Verification Commands

```bash
# Verify merged file content
cat /tmp/wt-user-a/src/app.py
# Expected: both greet and farewell changes present

# Verify audit log
python3 -c "
import sqlite3, json
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
rows = db.execute('''SELECT operation, status, detail FROM worktree_operations
                     WHERE operation IN ('merge','sync') ORDER BY created_at DESC LIMIT 5''').fetchall()
for r in rows: print(r)
"

# Verify backup branch exists
git -C /tmp/wt-user-a branch --list 'backup/*'
```

## Input Data

```python
# src/app.py -- User A's version (before merge)
def greet(name: str) -> str:
    """Return a personalized greeting message."""
    return f"Hello, {name}! Welcome to our project."

def farewell(name: str) -> str:
    """Return a farewell message."""            # unchanged
    return f"Goodbye, {name}!"                  # unchanged

# src/app.py -- User B's version
def greet(name: str) -> str:
    """Return a greeting message."""             # unchanged
    return f"Hello, {name}!"                     # unchanged

def farewell(name: str) -> str:
    """Return a warm farewell message."""
    return f"Goodbye, {name}! See you next time."

# src/app.py -- Expected merged result
def greet(name: str) -> str:
    """Return a personalized greeting message."""
    return f"Hello, {name}! Welcome to our project."

def farewell(name: str) -> str:
    """Return a warm farewell message."""
    return f"Goodbye, {name}! See you next time."
```

## Automation

- **pytest**: `automation/pytest/test_parallel_edit.py::test_different_parts_no_conflict`
- **Playwright**: Verify dashboard shows merge success, card transitions to "active"
