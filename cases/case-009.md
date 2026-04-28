# case-009: Manual Resolution with Edited Content

## Metadata

| Field | Value |
|-------|-------|
| ID | case-009 |
| Group | C -- Conflict Resolution |
| Priority | P0 |
| Conflict Expected | Detected then manually resolved |
| Spec Reference | Phase 4 -- `/resolve` with `content` field |

## Scenario

User manually writes a merged version that combines both changes:
multilingual support AND uppercase option. This is the "best of both" resolution.

## Preconditions

- Same conflict as case-002 on `src/app.py`

## Steps

### Step 1: User crafts merged content

The user writes a version that incorporates both features:

```python
def greet(name: str, lang: str = "en", uppercase: bool = False) -> str:
    """Return a greeting message with language and case options."""
    greetings = {"en": f"Hello, {name}!", "zh": f"你好，{name}！"}
    msg = greetings.get(lang, f"Hello, {name}!")
    return msg.upper() if uppercase else msg
```

### Step 2: Submit manual resolution

```bash
POST /api/projects/{pid}/worktrees/{wid}/resolve
{
  "file": "src/app.py",
  "resolution": "manual",
  "content": "def greet(name: str, lang: str = \"en\", uppercase: bool = False) -> str:\n    \"\"\"Return a greeting message with language and case options.\"\"\"\n    greetings = {\"en\": f\"Hello, {name}!\", \"zh\": f\"你好，{name}！\"}\n    msg = greetings.get(lang, f\"Hello, {name}!\")\n    return msg.upper() if uppercase else msg\n"
}
```

Backend:
```python
# Write content to src/app.py
# git add src/app.py
```

## Expected Results

| Check | Expected |
|-------|----------|
| `src/app.py` has `lang` parameter | Yes |
| `src/app.py` has `uppercase` parameter | Yes |
| Function signature | `greet(name, lang="en", uppercase=False)` |
| Multilingual greetings dict | Present |
| Uppercase logic | Present |
| Conflict markers | None |
| Audit log | `conflict_resolve` with `resolution: "manual"`, content NOT stored (too large) |

## Verification

```bash
# Verify merged content
python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('app', '/tmp/wt-user-a/src/app.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.greet('World') == 'Hello, World!'
assert mod.greet('World', lang='zh') == '你好，World！'
assert mod.greet('World', uppercase=True) == 'HELLO, WORLD!'
assert mod.greet('世界', lang='zh', uppercase=True) == '你好，世界！'
print('All assertions passed')
"
```

## Automation

- **pytest**: `automation/pytest/test_conflict_resolution.py::test_resolve_manual`
- **Playwright**:
  1. Open conflict panel for `src/app.py`
  2. Click "Edit Manually"
  3. Paste merged content in editor
  4. Click "Apply"
  5. Screenshot: verify both features visible in preview
