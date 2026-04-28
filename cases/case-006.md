# case-006: 3-Way Merge with Common Ancestor

## Metadata

| Field | Value |
|-------|-------|
| ID | case-006 |
| Group | B -- Conflict Detection |
| Priority | P1 |
| Conflict Expected | Partial (one file conflicts, one merges clean) |
| Spec Reference | Phase 3 -- WorktreeMergeService, SafetyGuard |

## Scenario

Both users diverge from the same commit on `main`. User A changes `src/app.py`
and `README.md`. User B changes `src/app.py` (conflicting) and `config.json`
(non-conflicting). The 3-way merge should detect conflict only on `src/app.py`,
while `README.md` and `config.json` merge cleanly.

## Preconditions

- Standard shared fixture
- Both branches diverged from the same `main` commit (common ancestor)

## Steps

### Step 1: Record common ancestor SHA

```bash
COMMON_SHA=$(git -C /tmp/wt-user-a rev-parse main)
echo "Common ancestor: $COMMON_SHA"
```

### Step 2: User A changes two files

```bash
cd /tmp/wt-user-a
```

Edit `src/app.py` -- modify `calculate()`:

```python
def calculate(a: int, b: int) -> int:
    """Return sum. Handles overflow gracefully."""
    result = a + b
    return min(result, 2**31 - 1)
```

Edit `README.md` -- add Usage section:

```markdown
## Usage

```python
from app import greet
print(greet("World"))
```
```

```bash
git add src/app.py README.md
git commit -m "feat: overflow protection + usage docs"
git push origin feat/user-a-task
```

### Step 3: User B changes `src/app.py` (conflicting) + `config.json` (clean)

```bash
cd /tmp/wt-user-b
```

Edit `src/app.py` -- different `calculate()` change:

```python
def calculate(a: int, b: int, *, allow_negative: bool = True) -> int:
    """Return sum. Optionally reject negative inputs."""
    if not allow_negative and (a < 0 or b < 0):
        raise ValueError("Negative values not allowed")
    return a + b
```

Edit `config.json` -- add new field:

```json
{
  "name": "test-project",
  "version": "1.0.0",
  "settings": {
    "debug": false,
    "log_level": "info",
    "cache_ttl": 300
  }
}
```

```bash
git add src/app.py config.json
git commit -m "feat: negative input guard + cache config"
git push origin feat/user-b-task
```

### Step 4: Merge User A's branch into main, then User B syncs

```bash
# Merge User A first (clean, no conflict on main)
# Then User B syncs -- rebase will conflict on src/app.py only
POST /api/projects/{pid}/worktrees/{wid-b}/sync
```

## Expected Results

| Check | Expected |
|-------|----------|
| Sync status | `conflict` |
| `conflict_files` | `["src/app.py"]` only |
| `config.json` merged cleanly | Yes (cache_ttl present in result) |
| `README.md` from User A pulled in | Yes (Usage section present) |
| Common ancestor respected | Git uses 3-way merge, not simple diff |
| Audit log | `sync` with `status=failed`, detail lists only `src/app.py` |

## Verification

```bash
# After conflict resolution (manual or via resolve API), verify 3-way result
git -C /tmp/wt-user-b log --oneline --graph
# Should show merge base, User A's commit, User B's commit

# Verify config.json has BOTH User A's and User B's additions
cat /tmp/wt-user-b/config.json
# Expected: has "cache_ttl": 300 from User B (merged cleanly)
```

## Automation

- **pytest**: `automation/pytest/test_conflict_detection.py::test_three_way_partial_conflict`
