# Live execution guard contract

Status: atomic admission primitive qualified; historical spent-problem deny refs live; legacy parent one-shot workflows retired.

A new protected scientific launcher MUST:
1. freeze a BRAIN_GUARDED_LAUNCH_PLAN_V1 file before execution;
2. set frozen.problem_sha256 to SHA-256("goal_text_v1\\0" + NFKC(goal_text).strip().lower() with whitespace collapsed);
3. pin every execution-critical task/runtime/authorization file by Git blob SHA-1 and/or SHA-256;
4. grant the job contents: write and expose GITHUB_TOKEN=${{ github.token }} only to the guard step;
5. invoke: python execution_guard/github_actions_guarded_run_live.py --plan <plan.json>
6. never invoke the scientific parent/Task-A/Task-B harness directly from workflow YAML.

The wrapper verifies the problem fingerprint and pins, atomically creates immutable gate + problem + run-ack refs in execution-guard/live-v1, strips GitHub tokens from the child environment, and only then starts the child command.

Semantics:
- one successful atomic admission, not exactly-once provider execution;
- any transport/rate-limit/ambiguous write fails closed and MUST NOT be retried automatically;
- existing problem identity blocks renamed PR/gate/runtime aliases;
- historical deny refs are authoritative replay barriers only for the six reviewed spent problems in HISTORICAL_SPENT_PROBLEMS_V1.json;
- PR335 was unspent and is intentionally absent from the spent set;
- repository-admin deletion/force-move of refs is outside the adapter guarantee while repository rules remain unprotected.
