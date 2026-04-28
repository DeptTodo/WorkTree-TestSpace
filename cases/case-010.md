# case-010: Multi-File Conflict Batch Resolution

## Metadata

| Field | Value |
|-------|-------|
| ID | case-010 |
| Group | C -- Conflict Resolution |
| Priority | P1 |
| Conflict Expected | Yes (multiple files) |
| Spec Reference | Phase 4 -- `/resolve` per file, Phase 5 -- WorktreeConflictPanel batch UI |

## Scenario

Three files have conflicts simultaneously. User resolves each with a different
strategy: file 1 with "ours", file 2 with "theirs", file 3 manually. All
resolutions happen in one session before completing the merge.

## Preconditions

- Merge or sync triggered that conflicts on 3 files simultaneously
- `conflict_files = ["src/app.py", "config.json", "README.md"]`

## Steps

### Step 1: Set up 3-file conflict

```bash
cd /tmp/wt-user-a
# Modify all three files with changes that conflict with User B's changes
```

User A changes:
- `src/app.py`: `greet()` signature change (as case-002)
- `config.json`: `settings.debug = true`
- `README.md`: rewrite title to "My Project v2"

User B changes (same files, different edits):
- `src/app.py`: different `greet()` signature
- `config.json`: `settings.debug = false, settings.cache = true`
- `README.md`: rewrite title to "Test Project -- Production"

### Step 2: Trigger merge -- expect 3-file conflict

```bash
POST /api/projects/{pid}/worktrees/{wid}/merge
{"targetBranch": "main", "strategy": "merge"}
```

Expected: `status: "conflict"`, `conflict_files: ["src/app.py", "config.json", "README.md"]`

### Step 3: Resolve file 1 -- "ours"

```bash
POST /api/projects/{pid}/worktrees/{wid}/resolve
{"file": "src/app.py", "resolution": "ours"}
```

### Step 4: Resolve file 2 -- "theirs"

```bash
POST /api/projects/{pid}/worktrees/{wid}/resolve
{"file": "config.json", "resolution": "theirs"}
```

### Step 5: Resolve file 3 -- "manual"

```bash
POST /api/projects/{pid}/worktrees/{wid}/resolve
{
  "file": "README.md",
  "resolution": "manual",
  "content": "# My Project v2 (Production)\n\nA sample project for worktree testing.\n\n## Features\n- Greeting\n- Farewell\n- Calculator\n"
}
```

### Step 6: Complete merge

After all 3 files resolved, the system should auto-complete the merge commit.

## Expected Results

| Check | Expected |
|-------|----------|
| `src/app.py` | User A's version (ours) |
| `config.json` | User B's version (theirs), has `cache: true` |
| `README.md` | Manual merge: "My Project v2 (Production)" |
| All conflict markers gone | Yes |
| Merge commit created | Yes |
| Worktree status | `active` |
| Audit log | 3 `conflict_resolve` entries + 1 `merge` success |

## Verification

```bash
# Verify each file
grep 'lang: str' /tmp/wt-user-a/src/app.py         # ours: present
grep 'cache' /tmp/wt-user-a/config.json             # theirs: present
grep 'Production' /tmp/wt-user-a/README.md           # manual: present

# Verify audit count
python3 -c "
import sqlite3
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
count = db.execute('''SELECT COUNT(*) FROM worktree_operations
                      WHERE operation='conflict_resolve' ''').fetchone()[0]
assert count == 3, f'Expected 3 resolves, got {count}'
print(f'OK: {count} conflict resolutions logged')
"
```

## Automation

- **pytest**: `automation/pytest/test_conflict_resolution.py::test_multi_file_batch_resolve`
- **Playwright**:
  1. Open conflict panel showing 3 conflicting files
  2. Resolve each file with different strategy
  3. Screenshot: resolved state with all 3 files cleared
  4. Verify "Merge Complete" success message
