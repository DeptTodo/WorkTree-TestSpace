# WorkTree Management Workflow -- Test Plan

> **Core Purpose**: Cover multi-user parallel development on the same project,
> focusing on concurrent file editing, conflict detection, and resolution.

## Test Case Index

### Group A: Parallel Edit Scenarios

| Case | Scenario | Conflict Expected |
|------|----------|-------------------|
| [case-001](../cases/case-001.md) | Two worktrees edit **different parts** of the same file | No (clean merge) |
| [case-002](../cases/case-002.md) | Two worktrees edit the **same part** of the same file | Yes (text conflict) |
| [case-003](../cases/case-003.md) | Two worktrees edit **different files** | No (clean merge) |

### Group B: Conflict Detection

| Case | Scenario | Trigger |
|------|----------|---------|
| [case-004](../cases/case-004.md) | Sync detects upstream conflict (rebase) | `sync()` on dirty worktree |
| [case-005](../cases/case-005.md) | Merge detects divergent changes | `merge()` with strategy |
| [case-006](../cases/case-006.md) | 3-way merge with common ancestor | Two branches diverge from same base |

### Group C: Conflict Resolution

| Case | Scenario | Strategy |
|------|----------|----------|
| [case-007](../cases/case-007.md) | Resolve with "ours" | Keep ours, discard theirs |
| [case-008](../cases/case-008.md) | Resolve with "theirs" | Keep theirs, discard ours |
| [case-009](../cases/case-009.md) | Manual resolution with edited content | User provides merged text |
| [case-010](../cases/case-010.md) | Multi-file conflict batch resolution | Resolve N files in one session |

### Group D: Safety Net (Loss Prevention)

| Case | Scenario | Safety Mechanism |
|------|----------|-----------------|
| [case-011](../cases/case-011.md) | Auto-stash on dirty worktree before destructive op | `SafetyGuard.stash_backup` |
| [case-012](../cases/case-012.md) | Backup branch creation before merge | `SafetyGuard.snapshot_branch` |
| [case-013](../cases/case-013.md) | Audit log trail for all operations | `worktree_operations` table |

### Group E: Boundary & Edge Cases

| Case | Scenario | Edge Condition |
|------|----------|----------------|
| [case-014](../cases/case-014.md) | 3+ worktrees concurrent editing same file | N-way contention |
| [case-015](../cases/case-015.md) | Edge cases: empty file, binary, uncommitted on create | Boundary conditions |

## Shared Test Fixture

All cases share a common git repository fixture defined in `fixtures/shared-repo.md`.

## Automation

- **Backend**: `automation/pytest/` -- pytest tests for SafetyGuard, SyncService, MergeService
- **Frontend**: `automation/playwright/` -- Playwright E2E for dashboard, conflict panel, dialogs
