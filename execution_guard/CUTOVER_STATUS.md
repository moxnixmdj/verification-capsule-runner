# Global execution guard cutover status

Status: **READY FOR LIVE CUTOVER**

Current design:
- atomic publication primitive: GitHub CREATE ref under `execution-guard/live-v1/<sha256(key)>`
- no protected coordination branch required for concurrent admission
- stable problem identity: `goal_text_v1_nfkc_lower_collapse_ws`
- gate identity and stable problem identity are both reserved before protected child execution
- ambiguous transport/rate-limit/write state fails closed with no automatic retry
- child starts only after gate + problem + current-run acknowledgement refs are confirmed

Verified before merge:
- original candidate: 28/28 tests PASS
- hardened historical reconciliation: 31/31 PASS
- final local suite: 39/39 PASS
- 24 competing processes: exactly one admitted side effect
- compact production implementation self-test: PASS
- live GitHub atomic-ref qualification: two simultaneous creates of one ref -> one success, one HTTP 422 Reference already exists
- six reviewed historical spent problem identities are already present as live deny refs
- PR335 stale SQLite parent task was explicitly unexecuted and is intentionally NOT seeded spent

Cutover changes in this PR:
- install `actions_admission.py`, `github_ref_store_live.py`, and `github_actions_guarded_run_live.py`
- delete the superseded mutable-branch Contents adapter
- delete eight obsolete direct parent/scientific one-shot workflows
- make launcher audit fail on any direct parent/Task-A/Task-B or direct ASTRA mission execution
- add lightweight PR/push regression workflow
- record the six live historical spent-problem refs and the future-launch contract

Guarantee scope:
- at-most-one successful guard admission per unchanged gate/problem key through this adapter
- not an exactly-once external execution guarantee
- repository-admin deletion/force-move of guard refs and direct commits that bypass repository review remain outside the adapter guarantee while repository rules are unprotected

No scientific task is executed by this cutover. No capability credit is authorized by it.
