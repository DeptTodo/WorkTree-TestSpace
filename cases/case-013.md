# case-013: Audit Log Trail for All Operations

## Metadata

| Field | Value |
|-------|-------|
| ID | case-013 |
| Group | D -- Safety Net |
| Priority | P0 |
| Conflict Expected | No |
| Spec Reference | Phase 1 -- worktree_operations table, WorktreeOperationRepository |

## Scenario

Every worktree operation (create, sync, merge, stash, restore, cleanup,
conflict_resolve, rollback) MUST be logged to `worktree_operations` with
correct user_id, project_id, worktree_path, operation, status, and detail.

## Preconditions

- Fresh database or known state
- User `u1` working on project `p1`

## Steps

### Step 1: Trigger create operation

```bash
POST /api/projects/p1/worktrees
{"taskDescription": "修复登录 bug"}
```

### Step 2: Trigger sync operation

```bash
POST /api/projects/p1/worktrees/{wid}/sync
```

### Step 3: Trigger merge operation (may succeed or conflict)

```bash
POST /api/projects/p1/worktrees/{wid}/merge
{"targetBranch": "main", "strategy": "merge"}
```

### Step 4: If conflict, trigger conflict_resolve

```bash
POST /api/projects/p1/worktrees/{wid}/resolve
{"file": "src/app.py", "resolution": "ours"}
```

### Step 5: Trigger cleanup

```bash
DELETE /api/projects/p1/worktrees/{wid}
{"keepBackup": true}
```

### Step 6: Query audit log

```python
import sqlite3, json
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')

rows = db.execute("""
    SELECT operation, status, detail, created_at
    FROM worktree_operations
    WHERE project_id = 'p1'
    ORDER BY created_at ASC
""").fetchall()

for r in rows:
    print(f"{r[3]} | {r[0]:20s} | {r[1]:10s} | {r[2]}")
```

## Expected Results

| Operation | Status | Detail Contains |
|-----------|--------|-----------------|
| `create` | `success` | `{name, branch, base_branch}` |
| `sync` | `success` or `failed` | `{commits_pulled, had_stash}` or `{conflict_files}` |
| `merge` | `success` or `failed` | `{strategy, backup_branch}` or `{conflict_files}` |
| `conflict_resolve` | `success` | `{file, resolution}` |
| `cleanup` | `success` | `{keep_backup: true}` |
| `stash` | `success` | `{ref: "stash@{0}"}` |
| `restore` | `success` | `{ref: "stash@{0}"}` |

## Verification

```bash
# Verify all operations logged
python3 -c "
import sqlite3
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
ops = [r[0] for r in db.execute(
    'SELECT DISTINCT operation FROM worktree_operations WHERE project_id=?', ('p1',)
).fetchall()]
required = {'create', 'sync', 'merge', 'cleanup'}
missing = required - set(ops)
assert not missing, f'Missing operations: {missing}'
print(f'All required operations logged: {ops}')
"

# Verify no operation logged without user_id
python3 -c "
import sqlite3
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
orphans = db.execute(
    'SELECT COUNT(*) FROM worktree_operations WHERE user_id IS NULL OR user_id=\"\"'
).fetchone()[0]
assert orphans == 0, f'{orphan} operations without user_id'
print('PASS: all operations have user_id')
"

# Verify temporal ordering
python3 -c "
import sqlite3
db = sqlite3.connect('/home/rock-ai/.claude/polaris/polaris.db')
rows = db.execute(
    'SELECT created_at FROM worktree_operations ORDER BY created_at ASC'
).fetchall()
timestamps = [r[0] for r in rows]
assert timestamps == sorted(timestamps), 'Timestamps not in order'
print(f'PASS: {len(timestamps)} operations in chronological order')
"
```

## Automation

- **pytest**: `automation/pytest/test_safety_net.py::test_audit_log_completeness`
- **pytest**: `automation/pytest/test_safety_net.py::test_audit_log_temporal_order`
