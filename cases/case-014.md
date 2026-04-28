# case-014: 3+ Worktrees Concurrent Editing Same File

## Metadata

| Field | Value |
|-------|-------|
| ID | case-014 |
| Group | E -- Boundary |
| Priority | P1 |
| Conflict Expected | Yes (multi-party) |
| Spec Reference | Phase 3 -- WorktreeMergeService, Phase 4 -- REST API |

## Scenario

Three users (A, B, C) all edit the same function `greet()` in `src/app.py`
simultaneously. User A merges first (clean). User B merges second (conflict
with A). User C merges third (conflict with A+B). Tests the system's ability
to handle N-way contention and sequential resolution.

## Preconditions

- Standard shared fixture with 3 worktrees
- User A at `/tmp/wt-user-a`, branch `feat/user-a-task`
- User B at `/tmp/wt-user-b`, branch `feat/user-b-task`
- User C at `/tmp/wt-user-c`, branch `feat/user-c-task`
- All diverged from same `main` commit

## Steps

### Step 1: All three users edit `greet()` concurrently

**User A** -- adds `title` parameter:
```python
def greet(name: str, title: str = "") -> str:
    """Return a greeting with optional title."""
    prefix = f"{title} " if title else ""
    return f"Hello, {prefix}{name}!"
```

**User B** -- adds `excited` parameter:
```python
def greet(name: str, excited: bool = False) -> str:
    """Return a greeting, optionally excited."""
    suffix = "!!!" if excited else "!"
    return f"Hello, {name}{suffix}"
```

**User C** -- adds `language` parameter:
```python
def greet(name: str, language: str = "en") -> str:
    """Return a greeting in specified language."""
    return {"en": f"Hello, {name}!", "es": f"Hola, {name}!", "zh": f"你好，{name}！"}.get(language, f"Hello, {name}!")
```

All three commit and push to their respective branches.

### Step 2: User A merges to main (clean -- first mover)

```bash
POST /api/projects/{pid}/worktrees/{wid-a}/merge
{"targetBranch": "main", "strategy": "merge"}
```

Expected: `status: "success"` (A's changes go into main)

### Step 3: User B syncs then merges (conflict with A)

```bash
# First sync to get A's changes
POST /api/projects/{pid}/worktrees/{wid-b}/sync

# Then merge
POST /api/projects/{pid}/worktrees/{wid-b}/merge
{"targetBranch": "main", "strategy": "merge"}
```

Expected: `status: "conflict"` (B's `excited` conflicts with A's `title`)

### Step 4: User B resolves conflict -- manual merge

```bash
POST /api/projects/{pid}/worktrees/{wid-b}/resolve
{
  "file": "src/app.py",
  "resolution": "manual",
  "content": "def greet(name: str, title: str = \"\", excited: bool = False) -> str:\n    prefix = f\"{title} \" if title else \"\"\n    suffix = \"!!!\" if excited else \"!\"\n    return f\"Hello, {prefix}{name}{suffix}\"\n"
}
```

### Step 5: User C syncs then merges (conflict with A+B)

```bash
POST /api/projects/{pid}/worktrees/{wid-c}/sync
POST /api/projects/{pid}/worktrees/{wid-c}/merge
{"targetBranch": "main", "strategy": "merge"}
```

### Step 6: User C resolves -- manual 3-way merge

```bash
POST /api/projects/{pid}/worktrees/{wid-c}/resolve
{
  "file": "src/app.py",
  "resolution": "manual",
  "content": "def greet(name: str, title: str = \"\", excited: bool = False, language: str = \"en\") -> str:\n    prefix = f\"{title} \" if title else \"\"\n    suffix = \"!!!\" if excited else \"!\"\n    base = {\"en\": \"Hello\", \"es\": \"Hola\", \"zh\": \"你好\"}.get(language, \"Hello\")\n    return f\"{base}, {prefix}{name}{suffix}\"\n"
}
```

## Expected Results

| Check | Expected |
|-------|----------|
| User A merge | `success` |
| User B merge | `conflict` -> manual resolve -> `success` |
| User C merge | `conflict` -> manual resolve -> `success` |
| Final `greet()` has all 3 features | `title`, `excited`, `language` |
| Audit log has 3 `create`, 3 `merge`, 2 `conflict_resolve` | Yes |
| All backup branches created | 3 backup branches under `backup/*` |
| No data loss at any stage | Each user's work recoverable from backup |

## Final Expected Function

```python
def greet(name: str, title: str = "", excited: bool = False, language: str = "en") -> str:
    prefix = f"{title} " if title else ""
    suffix = "!!!" if excited else "!"
    base = {"en": "Hello", "es": "Hola", "zh": "你好"}.get(language, "Hello")
    return f"{base}, {prefix}{name}{suffix}"
```

## Verification

```bash
# Verify final state
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('app', '/tmp/wt-user-c/src/app.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.greet('Alice', title='Dr.', excited=True, language='zh') == '你好, Dr. Alice!!!'
print('PASS: 3-way merge preserved all features')
"

# Verify 3 backup branches exist
git -C /tmp/wt-user-c branch --list 'backup/*' | wc -l
# Expected: 3
```

## Automation

- **pytest**: `automation/pytest/test_conflict_detection.py::test_three_way_concurrent_edit`
- **Playwright**:
  1. Dashboard shows 3 cards in "Has Conflict" column (after B and C's merges)
  2. Resolve each, verify cards move to "Active"
  3. Screenshot final state with all worktrees clean
