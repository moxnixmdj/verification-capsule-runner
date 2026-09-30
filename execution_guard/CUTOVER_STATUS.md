# Global execution guard cutover status

Status: **CANDIDATE INSTALLED ON BRANCH; NOT LIVE-ENFORCING YET**

Fresh bases at installation:
- runner main: `d9dfa39b0c8e2e2b8db2045aa772b45a02ffc487`
- Brain main: `adb12d9fc81ab9e2c9653266a7b7d08afe642cf7`

Verified locally before this branch:
- original package manifest: PASS
- original candidate suite: 28/28 PASS
- hardened suite after historical-reconciliation addition: 31/31 PASS
- 24 competing OS processes still produce exactly one admitted side effect
- SQLite reference-store connections are explicitly closed
- historical seed is dispatch-free, idempotent for exact evidence, rejects NOT_STARTED, and blocks later replay

This branch adds:
1. `one_shot_admission.py`: gate + problem dual reservation, no-retry uncertainty semantics, immutable terminal reconciliation, reviewed historical consumed-execution seeding.
2. `github_admission_store.py`: create-only GitHub Contents adapter with blob binding and fail-closed rate-limit/transport handling.
3. `launcher_audit.py`: release-blocking detector for scientific workflows that execute parent/Task-A/Task-B harnesses without `BRAIN_EXECUTION_GUARD_V1`.

## Why this is intentionally not merged as "live complete"

At refresh time both repository main branches reported `protected: false`. The available GitHub connector can create branches/files/PRs but exposes no branch-protection/ruleset mutation. The candidate's authority model requires the shared coordination branch to resist deletion, force-push/reset, and record edits. Pretending an unprotected branch is immutable would defeat the point of the guard.

Before live cutover:
1. create/choose the dedicated coordination branch and make it protected against force push, deletion, and direct record rewrite;
2. qualify create/read behavior on that exact branch with nonscientific fixtures;
3. reconcile historical consumed executions into the protected ledger before admitting new identities;
4. wrap every scientific launcher and child dispatch so reservation succeeds before the child process can start;
5. run `launcher_audit.py` and require zero bypasses;
6. only then merge/enable guarded launchers.

No scientific task was executed or replayed by this installation.
No capability credit is authorized by this branch.
