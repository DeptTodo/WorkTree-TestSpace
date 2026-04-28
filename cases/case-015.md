# case-015: Edge Cases -- Empty File, Binary, Uncommitted on Create

## Metadata

| Field | Value |
|-------|-------|
| ID | case-015 |
| Group | E -- Boundary |
| Priority | P1 |
| Conflict Expected | Varies per sub-case |
| Spec Reference | Phase 2 -- SafetyGuard, Phase 3 -- Sync/Merge services |

## Sub-Cases

### 15a: Empty file conflict

**Setup**: User A empties `config.json` (deletes all content), User B adds new fields.

```bash
cd /tmp/wt-user-a
echo -n "" > config.json
git add config.json && git commit -m "chore: remove config" && git push origin feat/user-a-task

cd /tmp/wt-user-b
echo '{"new_setting": true}' > config.json
git add config.json && git commit -m "feat: new config format" && git push origin feat/user-b-task
```

**Expected**: Merge detects conflict. Git marks it as `DD` (both deleted/modified).
Resolution: manual content required.

### 15b: Binary file handling

**Setup**: Both users add different binary files (images).

```bash
cd /tmp/wt-user-a
# Create a 1x1 red PNG
python3 -c "
import struct, zlib
def create_png(w, h, color):
    raw = b''
    for _ in range(h):
        raw += b'\x00' + bytes(color) * w
    compressed = zlib.compress(raw)
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')
with open('logo.png', 'wb') as f:
    f.write(create_png(1, 1, (255, 0, 0)))
"
git add logo.png && git commit -m "feat: add red logo" && git push origin feat/user-a-task

cd /tmp/wt-user-b
python3 -c "
# Same script but blue: (0, 0, 255)
# ... (create blue 1x1 PNG as logo.png)
"
git add logo.png && git commit -m "feat: add blue logo" && git push origin feat/user-b-task
```

**Expected**: Merge detects binary conflict. Git cannot auto-merge binary files.
Resolution: user must choose one version (ours/theirs).

### 15c: Worktree create with uncommitted changes in base

**Setup**: User has dirty working directory when requesting new worktree creation.

```bash
cd /tmp/wt-user-a
echo "uncommitted" >> src/app.py
# Now request worktree creation via API
POST /api/projects/{pid}/worktrees
{"taskDescription": "new feature while dirty"}
```

**Expected**:
- `SafetyGuard.stash_backup()` fires before worktree creation
- New worktree created from clean state
- Original worktree's dirty changes restored after creation
- Audit log: `stash` -> `create` -> `restore`

### 15d: Merge empty branch (no commits ahead)

**Setup**: User B has no new commits, tries to merge.

```bash
POST /api/projects/{pid}/worktrees/{wid-b}/merge
{"targetBranch": "main", "strategy": "merge"}
```

**Expected**: `status: "noop"` or clear error message. No backup branch needed.

### 15e: Concurrent sync from 2 users on same worktree

**Setup**: Two API calls to sync the same worktree simultaneously.

```bash
# Simulated concurrent requests
curl -X POST .../sync & curl -X POST .../sync &
```

**Expected**: One succeeds, other gets `409 Conflict` or both succeed
(idempotent). No corrupt state. Audit log has 2 entries.

## Expected Results Summary

| Sub-Case | Outcome | Data Loss? |
|----------|---------|------------|
| 15a empty file | Conflict detected, manual resolve | No |
| 15b binary file | Binary conflict, choose one | No |
| 15c dirty on create | Auto-stash, create, restore | No |
| 15d empty merge | Noop or error | N/A |
| 15e concurrent sync | Serialized or idempotent | No |

## Automation

- **pytest**: `automation/pytest/test_boundary.py::test_empty_file_conflict`
- **pytest**: `automation/pytest/test_boundary.py::test_binary_file_conflict`
- **pytest**: `automation/pytest/test_boundary.py::test_create_with_dirty_state`
- **pytest**: `automation/pytest/test_boundary.py::test_merge_noop`
- **pytest**: `automation/pytest/test_boundary.py::test_concurrent_sync`
