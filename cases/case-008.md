# case-008: Resolve Conflict with "theirs" Strategy

## Metadata

| Field | Value |
|-------|-------|
| ID | case-008 |
| Group | C -- Conflict Resolution |
| Priority | P0 |
| Conflict Expected | Detected then resolved |
| Spec Reference | Phase 4 -- `/resolve` endpoint |

## Scenario

Same conflict as case-002, but User A resolves by choosing "theirs" -- accepting
User B's `uppercase` version and discarding their own `lang` version.

## Preconditions

- Same as case-002: conflict on `src/app.py`

## Steps

### Step 1: Resolve with "theirs"

```bash
POST /api/projects/{pid}/worktrees/{wid}/resolve
{
  "file": "src/app.py",
  "resolution": "theirs"
}
```

Backend:
```python
# git checkout --theirs src/app.py
# git add src/app.py
```

## Expected Results

| Check | Expected |
|-------|----------|
| `src/app.py` content | User B's version: `greet(name, uppercase=False)` |
| `src/app.py` does NOT contain | User A's `lang` parameter |
| Conflict markers | Removed |
| Audit log | `conflict_resolve` with `resolution: "theirs"` |

## Verification

```bash
grep 'uppercase' /tmp/wt-user-a/src/app.py
# Expected: match (User B's version kept)

grep 'lang: str' /tmp/wt-user-a/src/app.py
# Expected: no match (User A's version discarded)
```

## Automation

- **pytest**: `automation/pytest/test_conflict_resolution.py::test_resolve_theirs`
- **Playwright**: Click "Keep Theirs", verify preview shows User B's content
