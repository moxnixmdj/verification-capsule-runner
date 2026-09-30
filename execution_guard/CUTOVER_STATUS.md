# Global execution guard cutover status

Status: **LIVE ON RUNNER MAIN**

Live runner commit that performed cutover: `f2335a12a5137f683b0660ec20aba6e45dc388cc` (PR #156).

Operational state:
- atomic publication primitive: GitHub CREATE ref under `execution-guard/live-v1/<sha256(key)>`
- protected-coordination-branch dependency removed
- stable problem identity: `goal_text_v1_nfkc_lower_collapse_ws`
- gate + stable problem + current-run acknowledgement are persisted before a protected child may start
- ambiguous transport, rate-limit, malformed response, or unconfirmed write fails closed; no automatic retry
- six reviewed historical spent problem identities are live as deny refs
- eight obsolete direct parent/scientific one-shot workflow entrypoints are deleted
- launcher regression audit rejects direct parent/Task-A/Task-B and direct ASTRA mission execution in workflow YAML
- future protected launchers must use `github_actions_guarded_run_live.py`

Verification:
- original candidate: 28/28 PASS
- hardened historical suite: 31/31 PASS
- final local suite: 39/39 PASS
- 24 competing processes: exactly one admitted side effect
- compact production self-test: PASS
- live GitHub qualification: concurrent create of one reservation ref -> one success, one HTTP 422 Reference already exists
- PR #156 exact-head Execution Guard Regression job: PASS (compile + repository-wide bypass audit)
- post-merge tree confirms all eight legacy launcher paths absent

Guarantee scope:
- at-most-one successful guard admission per unchanged gate/problem identity through this adapter
- not an exactly-once external provider execution guarantee
- repository-admin deletion/force-move of guard refs or a future direct bypass commit remains outside the adapter guarantee while repository rules are unprotected

PR335's stale SQLite parent task was never executed and is intentionally not seeded as spent.
No scientific task was executed by the cutover. No Brain capability credit was created.
