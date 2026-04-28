# case-007: Resolve Conflict with "ours" Strategy

## Metadata

| Field | Value |
|-------|-------|
| ID | case-007 |
| Group | C -- Conflict Resolution |
| Priority | P0 |
| Conflict Expected | Detected then resolved |
| Spec Reference | Phase 4 -- `/resolve` endpoint, Phase 5 -- WorktreeConflictPanel |

## Scenario

After case-002 detects a conflict on `src/app.py`, User A resolves it by choosing
"ours" -- keeping their version of `greet()` and discarding User B's.

## Preconditions

- Conflict already detected on `src/app.py` (from case-002 or equivalent)
- Worktree in conflict state: `conflict_files = ["src/app.py"]`
- User A's version: `greet(name, lang="en")` with multilingual support
- User B's version: `greet(name, uppercase=False)` with uppercase option

## Steps

### Step 1: Verify conflict state

```bash
GET /api/projects/{pid}/worktrees/{wid}
```

Expected: `conflictFiles: ["src/app.py"]`, `status: "conflict"`

### Step 2: Resolve with "ours"

```bash
POST /api/projects/{pid}/worktrees/{wid}/resolve
{
  "file": "src/app.py",
  "resolution": "ours"
}
```

Backend implementation:
```python
# git checkout --ours src/app.py
# git add src/app.py
```

### Step 3: Complete the merge

After all conflicts resolved, the merge can be completed:

```bash
# git commit (merge commit with resolved content)
# or git rebase --continue (if rebase path)
```

## Expected Results

| Check | Expected |
|-------|----------|
| Resolve API response | `200 OK` |
| `src/app.py` content | User A's version: `greet(name, lang="en")` with multilingual |
| `src/app.py` does NOT contain | User B's `uppercase` parameter |
| Conflict markers removed | Yes |
| Worktree status | `active` (conflict cleared) |
| Audit log | `conflict_resolve` with `detail: {"file": "src/app.py", "resolution": "ours"}` |
| `WorktreeConflict` event (resolved) | Emitted |

## Verification Commands

```bash
# Verify file content is "ours"
grep 'lang: str' /tmp/wt-user-a/src/app.py
# Expected: match (User A's version)

grep 'uppercase' /tmp/wt-user-a/src/app.py
# Expected: no match (User B's version discarded)

# Verify no conflict markers remain
grep -c '<<<<<<' /tmp/wt-user-a/src/app.py
# Expected: 0

# Verify audit log
python3 -c "
import sqlite3
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
rows = db.execute('''SELECT operation, detail FROM worktree_operations
                     WHERE operation='conflict_resolve' ORDER BY created_at DESC LIMIT 1''').fetchall()
print(rows)
"
```

## Automation

- **pytest**: `automation/pytest/test_conflict_resolution.py::test_resolve_ours`
- **Playwright**:
  1. Open conflict panel, click "Keep Ours" on `src/app.py`
  2. Verify file preview shows User A's content
  3. Screenshot resolved state
