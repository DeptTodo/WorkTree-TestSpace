# case-003: Two Worktrees Edit Different Files

## Metadata

| Field | Value |
|-------|-------|
| ID | case-003 |
| Group | A -- Parallel Edit |
| Priority | P0 |
| Conflict Expected | No (clean merge) |
| Spec Reference | Phase 3 -- WorktreeMergeService |

## Scenario

User A edits `src/app.py`, User B edits `README.md`. No file overlap at all.
Merge should be trivially clean.

## Preconditions

- Standard shared fixture (see `fixtures/shared-repo.md`)
- User A worktree at `/tmp/wt-user-a`, branch `feat/user-a-task`
- User B worktree at `/tmp/wt-user-b`, branch `feat/user-b-task`

## Steps

### Step 1: User A adds a new function to `src/app.py`

```bash
cd /tmp/wt-user-a
```

Append to `src/app.py`:

```python
def multiply(a: int, b: int) -> int:
    """Return product of two numbers."""
    return a * b
```

```bash
git add src/app.py
git commit -m "feat: add multiply function"
git push origin feat/user-a-task
```

### Step 2: User B adds a section to `README.md`

```bash
cd /tmp/wt-user-b
```

Append to `README.md`:

```markdown
## Installation

```bash
pip install test-project
```
```

```bash
git add README.md
git commit -m "docs: add installation section"
git push origin feat/user-b-task
```

### Step 3: Merge via WorktreeMergeService

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
| Merge status | `success` |
| `conflict_files` | `[]` |
| `src/app.py` has `multiply()` | Yes |
| `README.md` has Installation section | Yes |
| Audit log | `merge` with `status=success` |

## Automation

- **pytest**: `automation/pytest/test_parallel_edit.py::test_different_files_no_conflict`
