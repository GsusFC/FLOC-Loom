# FLOC*Loom operations

This reference owns executable workflow mechanics: companion-agent preflight, runtime
observation, ledger evidence capture, and maintenance. It does **not** choose the route;
read [SKILL.md](../SKILL.md) first for the normative `solo|delegate|audit|full` policy,
and read [role-contracts.md](role-contracts.md) for role and final-review semantics.

## 1. Resolve plugin-local helpers

Always resolve helpers from this skill directory, never from a caller's current
directory:

~~~sh
skill_dir=<directory-containing-SKILL.md>
installer="$skill_dir/../../scripts/install-agents.sh"
ledger="$skill_dir/../../scripts/ledger.py"
runtime_inspector="$skill_dir/../../scripts/inspect-agent-runtime.sh"
~~~

## 2. Preflight companion agents

Run the all-role exactness check before delegation:

~~~sh
sh "$installer" --check
~~~

Use a role-scoped non-mutating preflight only when diagnosing that one role:

~~~sh
sh "$installer" --check-role luna
sh "$installer" --check-role terra
sh "$installer" --check-role sol
~~~

A missing role file has one executable exit after required approval:

~~~sh
sh "$installer"
sh "$installer" --check
~~~

The installer adds missing files and may migrate an allowlisted byte-exact historical
Sol reviewer. It never overwrites an arbitrary differing file. A migration/check
refusal names the shipped source and local destination; reconcile a user-owned conflict
or remove a deliberately unwanted file, then rerun the same command. Do not replace a
role with a built-in agent. Start a fresh Codex task after any successful install or
migration so native custom roles are rediscovered.

## 3. Capture native routing evidence

Use public spawn/details metadata first. When it does not reveal required model or
effort, use the local read-only inspector against the exact native thread id:

~~~sh
sh "$runtime_inspector" \
  --expected-role <expected-role> \
  --expected-model <expected-model> \
  --expected-effort <expected-effort> \
  <native-subagent-thread-id>
~~~

For a Sol review, require actual isolation fields as well:

~~~sh
sh "$runtime_inspector" \
  --expected-role floc_loom_sol_reviewer \
  --expected-model gpt-5.6-sol \
  --expected-effort high \
  --require-sandbox-type read-only \
  --require-permission-profile \
  <native-review-thread-id>
~~~

The helper emits only allowlisted routing metadata. It is not a prompt, rollout, or
runtime-data inspector. If public and local values both exist, they must agree. Stop
when role/model/effort/sandbox/permission evidence is absent or inconsistent.

## 4. Initialize a route-scoped ledger

Create one ledger for each non-solo direct deliverable or graph node, before its first
mutation or auxiliary spawn. `solo` intentionally has no ledger. Keep the evidence root
outside the repository:

~~~sh
repo=/absolute/path/to/repository
runs_root=/absolute/path/to/runs
run_id=<lowercase-uuid>

python3 "$ledger" init \
  --repo "$repo" \
  --ledger-root "$runs_root" \
  --run-id "$run_id" \
  --route <delegate|audit|full> \
  --owned-file src/example.py \
  --owned-file tests/test_example.py
run_dir="$runs_root/$run_id"
~~~

`init` persists the declared route immutably. If the work becomes stronger, record the
change before performing the stronger work:

~~~sh
python3 "$ledger" escalate \
  --ledger "$run_dir" \
  --to full \
  --reason 'The node crossed the high-risk integration boundary.'
~~~

Escalation is monotonic. A ledger does not support downgrade. If `delegate` already has
worker evidence, escalating to `audit` is refused because the audit matrix forbids
worker evidence; use `full` or start a new audit deliverable instead.

## 5. Record worker and verification evidence

After accepted runtime routing evidence, record one implementation worker only when the
route requires it:

~~~sh
python3 "$ledger" record-worker \
  --ledger "$run_dir" \
  --thread-id <thread-id> \
  --role <observed-role> \
  --model <observed-model> \
  --effort <observed-effort> \
  --cwd <observed-cwd>
~~~

Capture each primary-session verification command in an evidence file outside the
repository, then record the actual exit code. `record-verification` hashes that file
and binds the evidence to the repository snapshot visible at recording time:

~~~sh
<exact-verification-command> > /absolute/path/to/verification-output.txt 2>&1
exit_code=$?
python3 "$ledger" record-verification \
  --ledger "$run_dir" \
  --command '<exact-verification-command>' \
  --exit-code "$exit_code" \
  --evidence-file /absolute/path/to/verification-output.txt
~~~

A non-zero verification may be recorded for diagnosis but cannot be accepted. Do not
place request bodies, prompts, credentials, full URLs, environment/configuration values,
or other sensitive runtime payloads in evidence files intended for review distribution.

## 6. Accept `delegate`

A reviewer-free delegate is valid only for one Luna worker, passing verification, and
an unchanged verified repository state. Immediately after the final successful
verification record:

~~~sh
python3 "$ledger" snapshot --ledger "$run_dir" --label verified-state
python3 "$ledger" accept --ledger "$run_dir"
~~~

Any mutation after `verified-state`, altered evidence file, Terra worker, Sol review,
extra worker, missing verification binding, or out-of-scope change fails closed.

## 7. Accept `audit` or `full`

`audit` records no worker. `full` records exactly one Luna or Terra worker. Both record
primary verification, capture the repository immediately before and after the fresh Sol
review, and record its verdict:

~~~sh
python3 "$ledger" snapshot --ledger "$run_dir" --label before-review
# Spawn floc_loom_sol_reviewer with the final-review packet from role-contracts.md.
python3 "$ledger" snapshot --ledger "$run_dir" --label after-review
~~~

For every audit/full final review, first inspect the public exact coverage mapping and
artifact schema from the same shipped ledger that will validate the review:

~~~sh
python3 "$ledger" coverage-schema --json | jq .
~~~

The command is deterministic and dependency-free; it emits every allowed trigger and
category ID, their semantic text, required fields, validation rules, and a fingerprint
that the shipped verifier binds to
[role-contracts.md](role-contracts.md#conditional-security-and-observability-sweep).
That role-contract reference remains the semantic source for when and why the sweep
applies. Use the emitted IDs verbatim to create the compact coverage file; do not
hand-copy an example or inspect ledger implementation internals. The file records only
identifiers and short non-sensitive exclusions—not runtime payloads.

The ledger requires every allowed category to appear exactly once in `inspected` or
`exclusions`. For a non-triggered sweep, use no triggers, no inspected categories, and
a short non-sensitive exclusion for every category. It rejects duplicate/unknown IDs,
incomplete coverage, multiline justifications, and common payload/value markers.

Record the review and accept:

~~~sh
python3 "$ledger" record-review \
  --ledger "$run_dir" \
  --thread-id <review-thread-id> \
  --role floc_loom_sol_reviewer \
  --model gpt-5.6-sol \
  --effort high \
  --cwd <observed-cwd> \
  --sandbox-policy-type <observed-sandbox-policy> \
  --permission-profile-type <observed-permission-profile> \
  --verdict <ship|fix-first|rethink> \
  --reason '<evidence-based reason>' \
  --residual-risk '<none or explicit residual risk>' \
  --coverage-file /absolute/path/to/review-coverage.json
python3 "$ledger" accept --ledger "$run_dir"
~~~

Hard `read-only` isolation is required by default. When hard isolation is not required
and the host broadens the reviewer sandbox, record the actual residual risk and add
`--allow-behavioral-read-only` to `accept`. That mode is behaviorally read-only, never
OS-enforced isolation.

## 8. Handle a review correction

The final-review packet declares `REVIEW CYCLE: initial` or
`post-fix-first-bundle`. On an initial `fix-first`, group every known blocker for that
review boundary into one correction bundle, independently verify it, then spawn a fresh
review with `post-fix-first-bundle`. A newly found blocker there is `rethink`; do not
run another automatic patch cycle.

This workflow deliberately has no native correction-count ledger state machine. The
packet's boundary and fresh reviewer make the decision auditable without adding a new
state, flag, or global budget.

## 9. Maintain and validate the plugin

Run the repository checks after changes:

~~~sh
python3 -m unittest plugins/floc-loom/scripts/test_ledger.py
sh plugins/floc-loom/scripts/test_install_agents.sh
sh plugins/floc-loom/scripts/verify.sh
git diff --check
~~~

The installer fixture covers role-scoped checks, exact v0.4 Sol migration, modified
file refusal, all-mutation preflight, and parent/destination symlink refusal. Keep it
with installer behavior so a migration cannot silently weaken user-owned-file safety.
