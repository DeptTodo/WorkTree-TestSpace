# case-002: Two Worktrees Edit Same Part of Same File

## Metadata

| Field | Value |
|-------|-------|
| ID | case-002 |
| Group | A -- Parallel Edit |
| Priority | P0 (critical path) |
| Conflict Expected | **Yes (text conflict)** |
| Spec Reference | Phase 3 -- WorktreeMergeService conflict path, Phase 5 -- WorktreeConflictPanel |

## Scenario

User A and User B both modify the `greet()` function signature and body in `src/app.py`.
Their changes overlap on the same lines -- merge MUST detect a text conflict.

## Preconditions

- Shared origin repo at `/tmp/wt-test-origin.git` with `main` branch
- User A worktree at `/tmp/wt-user-a` on branch `feat/user-a-task`
- User B worktree at `/tmp/wt-user-b` on branch `feat/user-b-task`
- Both branches up-to-date with `origin/main`

## Steps

### Step 1: User A modifies `greet()` -- adds language parameter

```bash
cd /tmp/wt-user-a
```

Edit `src/app.py` lines 6-8:

```python
def greet(name: str, lang: str = "en") -> str:
    """Return a greeting message in specified language."""
    greetings = {"en": f"Hello, {name}!", "zh": f"你好，{name}！"}
    return greetings.get(lang, f"Hello, {name}!")
```

```bash
git add src/app.py
git commit -m "feat: add multilingual greeting"
git push origin feat/user-a-task
```

### Step 2: User B modifies `greet()` -- adds uppercase option

```bash
cd /tmp/wt-user-b
```

Edit `src/app.py` lines 6-8:

```python
def greet(name: str, uppercase: bool = False) -> str:
    """Return a greeting message, optionally uppercased."""
    msg = f"Hello, {name}!"
    return msg.upper() if uppercase else msg
```

```bash
git add src/app.py
git commit -m "feat: add uppercase greeting option"
git push origin feat/user-b-task
```

### Step 3: User A attempts to merge User B's changes

```bash
POST /api/projects/{pid}/worktrees/{wid}/merge
{
  "targetBranch": "main",
  "strategy": "merge"
}
```

## Expected Results

| Check | Expected |
|-------|----------|
| Merge status | `conflict` |
| `conflict_files` | `["src/app.py"]` |
| `conflict_risk` | `high` |
| `WorktreeConflict` event emitted | Yes, with `operation="merge"` |
| Backup branch still created | Yes (snapshot before merge attempt) |
| Merge aborted | Yes (`git merge --abort` executed) |
| Original state preserved | User A's worktree unchanged (pre-merge state) |
| Audit log | `merge` operation with `status=failed`, detail contains conflict info |

## Conflict Content (what git produces)

```
<<<<<<< HEAD
def greet(name: str, lang: str = "en") -> str:
    """Return a greeting message in specified language."""
    greetings = {"en": f"Hello, {name}!", "zh": f"你好，{name}！"}
    return greetings.get(lang, f"Hello, {name}!")
=======
def greet(name: str, uppercase: bool = False) -> str:
    """Return a greeting message, optionally uppercased."""
    msg = f"Hello, {name}!"
    return msg.upper() if uppercase else msg
>>>>>>> feat/user-b-task
```

## Verification Commands

```bash
# Verify conflict detected via API
curl -s http://localhost:3210/api/projects/$PID/worktrees/$WID \
  -H "Authorization: Bearer $TOKEN" | jq '.conflictFiles'
# Expected: ["src/app.py"]

# Verify backup branch exists (merge was attempted but aborted)
git -C /tmp/wt-user-a branch --list 'backup/*'

# Verify worktree state is clean (merge aborted successfully)
git -C /tmp/wt-user-a status --porcelain
# Expected: empty (no dirty files)

# Verify audit log
python3 -c "
import sqlite3
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
rows = db.execute('''SELECT operation, status, detail FROM worktree_operations
                     WHERE operation='merge' ORDER BY created_at DESC LIMIT 1''').fetchall()
print(rows)
# Expected: ('merge', 'failed', '{"conflict_files": ["src/app.py"], ...}')
"
```

## Input Data Summary

| User | Function Signature | Change Area |
|------|-------------------|-------------|
| A | `greet(name, lang="en")` | Lines 6-8 (adds multilingual) |
| B | `greet(name, uppercase=False)` | Lines 6-8 (adds uppercase) |

Both modify the exact same lines 6-8 -- guaranteed text conflict.

## Automation

- **pytest**: `automation/pytest/test_conflict_detection.py::test_same_lines_conflict`
- **Playwright**:
  1. Verify conflict card appears in dashboard "Has Conflict" column
  2. Screenshot conflict panel showing `src/app.py` with ours/theirs blocks
  3. Verify backup branch info displayed on card
