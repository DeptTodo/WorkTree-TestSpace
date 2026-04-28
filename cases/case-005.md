# case-005: Merge Detects Divergent Changes (Three Strategies)

## Metadata

| Field | Value |
|-------|-------|
| ID | case-005 |
| Group | B -- Conflict Detection |
| Priority | P0 |
| Conflict Expected | **Yes (merge strategy), No (rebase on clean history)** |
| Spec Reference | Phase 3 -- WorktreeMergeService |

## Scenario

User A and User B both modify `config.json` settings. Test merge detection across
all three strategies: `merge`, `squash`, `rebase`. The `merge` and `squash` strategies
detect conflicts at merge time; `rebase` detects at rebase time.

## Preconditions

- Standard shared fixture
- Both users have diverged from `main` with conflicting `config.json` changes

## Steps

### Step 1: User A modifies `config.json` -- changes log_level

```bash
cd /tmp/wt-user-a
```

Edit `config.json`:

```json
{
  "name": "test-project",
  "version": "1.0.0",
  "settings": {
    "debug": true,
    "log_level": "debug",
    "max_retries": 3
  }
}
```

```bash
git add config.json
git commit -m "feat: enable debug mode with retries"
git push origin feat/user-a-task
```

### Step 2: User B modifies `config.json` -- changes different + overlapping fields

```bash
cd /tmp/wt-user-b
```

Edit `config.json`:

```json
{
  "name": "test-project",
  "version": "1.1.0",
  "settings": {
    "debug": false,
    "log_level": "warning",
    "timeout": 30
  }
}
```

```bash
git add config.json
git commit -m "feat: bump version, add timeout setting"
git push origin feat/user-b-task
```

### Step 3a: Test merge strategy -- expect conflict

```bash
POST /api/projects/{pid}/worktrees/{wid-a}/merge
{
  "targetBranch": "main",
  "strategy": "merge"
}
```

### Step 3b: Test squash strategy -- expect conflict

```bash
# Reset and retry with squash (on a clean copy or after abort)
POST /api/projects/{pid}/worktrees/{wid-a}/merge
{
  "targetBranch": "main",
  "strategy": "squash",
  "commitMsg": "feat: combined changes"
}
```

### Step 3c: Test rebase strategy -- expect conflict

```bash
POST /api/projects/{pid}/worktrees/{wid-b}/merge
{
  "targetBranch": "main",
  "strategy": "rebase"
}
```

## Expected Results -- Per Strategy

### merge strategy

| Check | Expected |
|-------|----------|
| Status | `conflict` |
| `conflict_files` | `["config.json"]` |
| Backup branch exists | Yes |
| Merge aborted | Yes |
| `git status` clean | Yes (after abort) |

### squash strategy

| Check | Expected |
|-------|----------|
| Status | `conflict` |
| `conflict_files` | `["config.json"]` |
| No partial squash commit | Yes |

### rebase strategy

| Check | Expected |
|-------|----------|
| Status | `conflict` |
| `conflict_files` | `["config.json"]` |
| Rebase aborted | Yes |
| Original commits preserved | Yes |

## Conflict Content (config.json)

```json
{
<<<<<<< HEAD
  "name": "test-project",
  "version": "1.0.0",
  "settings": {
    "debug": true,
    "log_level": "debug",
    "max_retries": 3
  }
=======
  "name": "test-project",
  "version": "1.1.0",
  "settings": {
    "debug": false,
    "log_level": "warning",
    "timeout": 30
  }
>>>>>>> feat/user-b-task
}
```

## Automation

- **pytest**: `automation/pytest/test_conflict_detection.py::test_merge_strategy_conflict`
- **pytest**: `automation/pytest/test_conflict_detection.py::test_squash_strategy_conflict`
- **pytest**: `automation/pytest/test_conflict_detection.py::test_rebase_strategy_conflict`
- **Playwright**: Merge dialog shows strategy radio buttons, conflict panel shows `config.json`
