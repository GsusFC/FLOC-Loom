---
name: orchestration
description: "Codex-native architect, setup, and delegation workflow that uses separately installed, role-pinned custom agents: GPT-5.6 Luna at max reasoning as the preferred implementer for well-specified frontend/backend nodes, GPT-5.6 Terra at max reasoning for capability and high-risk escalation, and a fresh GPT-5.6 Sol reviewer at high reasoning with observed sandbox evidence. Use for FLOC*Loom installation or onboarding, delegated implementation, adaptive execution graphs, parallel or stacked deliverables, frontend/backend/full-stack work, feature work, bug fixes, refactors, lane selection, five-part implementation specs, execution-ledger evidence, verification of subagent work, commitment-boundary advice, or any deliverable that must receive a final independent-context Sol review before acceptance."
---

# FLOC*Loom Orchestration

Act as the architect. Own the user's intent, architecture, dependency graph, routing,
verification, and final acceptance. Delegate implementation volume to the least
expensive adequate lane without treating price as evidence of capability, then obtain a
fresh Sol verdict before reporting a deliverable complete. The implementation and
reviewer lanes are native Codex custom-agent threads, not a nested Codex CLI wrapper or
a global default-subagent setting.

Read [references/role-contracts.md](references/role-contracts.md) before the first
delegation in a session. It defines the required implementation spec, reports, and
review packet.

Read [references/execution-graphs.md](references/execution-graphs.md) before planning a
multi-deliverable, parallel, stacked-PR, frontend/backend, or full-stack build. It
defines graph nodes, safe scheduling, lane eligibility, domain verification, and
integration acceptance.

## Confirm the primary session

Run the primary Codex session on gpt-5.6-sol with high reasoning. Verify the current
model and effort when the runtime exposes them. If either setting differs, tell the
user how to select Sol / High and stop before delegation. If the runtime does not
expose the settings, ask the user to confirm that Sol / High is selected and stop
until they confirm. A skill cannot change the primary session's model itself; never
assume or claim that this prerequisite is satisfied.

## Preflight the companion custom agents

The three role files are user-owned native custom-agent TOML files. Installing or
updating this plugin does **not** install, overwrite, or register them automatically.
They must be installed separately and a fresh Codex task must be started so the native
spawn tool can discover the current roles.

Before every delegation, complete steps 1–2. After spawning a lane, complete steps
3–4 before accepting any result:

1. From the directory containing this SKILL.md, resolve
   ../../scripts/install-agents.sh; never resolve it from the caller's current
   directory. Run its non-mutating exactness check:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   installer="$skill_dir/../../scripts/install-agents.sh"
   sh "$installer" --check
   ~~~

   It must exit zero. That proves every installed role file is byte-for-byte identical
   to the shipped template. If it reports only missing files, offer to run the same
   installer once without `--check`. That operation writes user-owned Codex agent
   profiles, so obtain the required user/tool approval before running it. The installer
   adds only missing files and performs its own exactness check. After it succeeds,
   stop and tell the user to start a new Codex task because native agent types are
   discovered at task creation.

   If the check reports a stale, differing, symlinked, or otherwise conflicting file,
   do not run the installer automatically: it intentionally refuses replacement. Give
   the user the exact source and destination paths and ask them to reconcile the
   conflict deliberately. Do not work around either state by choosing another agent.

2. Inspect the native spawn tool's available agent_type entries. All three names must
   be exposed exactly before any lane may run:

   - floc_loom_luna_implementer
   - floc_loom_terra_implementer
   - floc_loom_sol_reviewer

   If a name is missing or unavailable, stop the affected lane and tell the user to
   install/check the companion files, start a fresh task, and update Codex if the name
   is still not exposed. Never substitute a built-in role or a similarly named agent.

3. Treat byte-exact templates plus observed runtime routing as an acceptance gate. Use
   public native spawn/details metadata first. It must identify the selected custom
   role; when it also exposes model and effort, compare them with the pinned lane.

   If public details omit model or effort and the local rollout is accessible, resolve
   ../../scripts/inspect-agent-runtime.sh relative to this SKILL.md and run it against
   the spawned native thread id:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   runtime_inspector="$skill_dir/../../scripts/inspect-agent-runtime.sh"
   sh "$runtime_inspector" \
     --expected-role <expected-role> \
     --expected-model <expected-model> \
     --expected-effort <expected-effort> \
     <native-subagent-thread-id>
   ~~~

   This read-only helper locates only the exact local rollout filename for that id and
   emits an allowlisted routing object. The expected flags make the helper fail on a
   role/model/effort mismatch instead of leaving comparison to memory. It is the
   authoritative local fallback for omitted model and effort, not a replacement agent
   or an inferred guess. If both public details and the helper expose a value, they must
   agree.

   The accepted values remain Luna / max for preferred bounded implementation, Terra /
   max for escalation, and Sol / high for review. If the selected role, model, or
   effort is missing, inconsistent, unavailable, or unobservable after this procedure,
   stop that lane with an actionable error and do not accept its report as routed work.
   Never silently fall back to another model, effort, or agent type.

4. Always inspect and report the reviewer's observed sandbox policy type and permission
   profile type from public details, or from the local helper when public details omit
   them. For the local fallback, require both fields explicitly:

   ~~~sh
   sh "$runtime_inspector" \
     --expected-role floc_loom_sol_reviewer \
     --expected-model gpt-5.6-sol \
     --expected-effort high \
     --require-sandbox-type read-only \
     --require-permission-profile \
     <native-review-thread-id>
   ~~~

   The shipped reviewer file requests read-only sandboxing; a host permission profile
   can broaden that request. Do not call the review OS-enforced read-only unless the
   observed sandbox policy type is read-only.

The custom-agent file, not the spawn call, pins each model and reasoning effort. Do
not add a per-spawn model or reasoning override anywhere in this workflow.

## Choose direct execution or an adaptive graph

Use a direct five-part implementation spec for one bounded, independently verifiable
change. Do not create graph ceremony when there is no useful dependency or concurrency
decision.

For two or more material deliverables, cross-domain work, parallel execution, or
stacked PRs, build the adaptive execution graph from `references/execution-graphs.md`
before delegation. The graph is a delivery DAG, not automatically a PR graph: choose a
task, commit, or PR boundary according to review and rollback needs. Branch, commit, and
PR creation still require the user's authorization.

The primary session owns graph state. Start a node only when its dependencies are
accepted, its interfaces are settled, and its file ownership does not overlap another
active node. Add an integration node whenever correctness emerges across node or
frontend/backend boundaries. Worker reports do not advance a node to verified or
accepted without primary evidence and the required review gate.

## Record an execution ledger

The skill's instructions are not a host-level hook. Use the companion ledger as the
fail-closed acceptance gate, and do not report completion unless `accept` succeeds.
Resolve it relative to this skill; never resolve it from the caller's working directory:

~~~sh
skill_dir=<directory-containing-this-SKILL.md>
ledger="$skill_dir/../../scripts/ledger.py"
~~~

Initialize one ledger per deliverable with the complete allowed file set:

~~~sh
python3 "$ledger" init \
  --repo <repository> \
  --ledger-root <runs-root> \
  --run-id <lowercase-uuid> \
  --owned-file <file-or-directory> \
  [--owned-file <another-file-or-directory>]
run_dir=<runs-root>/<lowercase-uuid>
~~~

After each worker's public-details-first routing evidence is accepted, record the exact
observed role, model, effort, thread, and working directory. Use one `record-worker`
call per worker, including parallel non-overlapping workers:

~~~sh
python3 "$ledger" record-worker \
  --ledger "$run_dir" \
  --thread-id <thread-id> \
  --role <observed-role> \
  --model <observed-model> \
  --effort <observed-effort> \
  --cwd <observed-cwd>
~~~

Capture every primary-session verification command to a file and record its exit code
and immutable evidence hash. A non-zero result cannot be accepted:

~~~sh
python3 "$ledger" record-verification \
  --ledger "$run_dir" \
  --command '<exact-command>' \
  --exit-code <actual-exit-code> \
  --evidence-file <captured-output-file>
~~~

Immediately before spawning the final reviewer, capture `before-review`; immediately
after it returns, capture `after-review`. Record the observed reviewer metadata and its
single verdict, then run the gate:

~~~sh
python3 "$ledger" snapshot --ledger "$run_dir" --label before-review
<spawn the fresh reviewer and capture its exact report>
python3 "$ledger" snapshot --ledger "$run_dir" --label after-review
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
  --residual-risk '<none or explicit residual risk>'
python3 "$ledger" accept --ledger "$run_dir"
~~~

The gate checks role/model/effort pins, verification evidence, review verdict, exact
before/after repository state, evidence-file integrity, and changed-file scope. It
requires observed `read-only` isolation by default. Use
`--allow-behavioral-read-only` only when hard isolation is not required and the review
reports the broader sandbox as residual risk. That mode must never be described as
OS-enforced read-only.

## Keep architect work in the primary session

Keep these responsibilities in the primary session:

- Resolve requirements and material ambiguity.
- Choose architecture, interfaces, and decomposition.
- Select the implementation lane.
- Write the complete five-part spec.
- Inspect the actual diff and rerun verification.
- Judge reviewer feedback and accept the deliverable.

Do not type implementation code, tests, boilerplate, or mechanical configuration in
the primary session when a lane can do it. If a lane's result is wrong, correct the
spec and delegate the fix rather than silently repairing it yourself.

## Route implementation

### Luna: preferred bounded implementation lane

Use Luna Max first for bounded frontend, backend, and full-stack nodes after Sol has
settled the architecture, interfaces, ownership, constraints, and verification. Luna
may own feature-level implementation when the node is coherent and the specification
makes its important behavior and failure cases explicit; it is not limited to
boilerplate or mechanical edits.

Do not route unsettled design or architecture decisions to Luna. Route unusually
high-risk security, migration, concurrency, distributed-effects, deep debugging, or
broad integration work to Terra when it cannot be bounded safely. If design is
unsettled, stop and return the decision to the studio. After a failed Luna attempt,
inspect the evidence: correct a genuine specification gap and allow one fresh Luna
attempt, or escalate immediately when the failure shows a capability/context mismatch.
Escalate after a corrected Luna attempt also fails.

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_luna_implementer
fork_turns: none
~~~

Its installed agent file pins GPT-5.6 Luna at max reasoning. Do not include a
per-spawn model or reasoning field. Confirm the public-details-first runtime evidence,
using the local inspector only when those details omit model or effort, before
accepting any work; if it is unavailable or differs, stop the lane rather than falling
back.

### Terra: capability and high-risk escalation lane

Use Terra when a node cannot be bounded reliably for Luna or correctness depends on
unusually broad context or technical judgment. Typical cases include subtle
concurrency, non-trivial algorithms, security-sensitive paths, migration design,
distributed effects, difficult production debugging, broad refactors, or large
cross-module integration. Terra is not a design authority. Also escalate when Luna's
evidence demonstrates a capability/context mismatch or a corrected Luna attempt fails.
Correct the specification before retrying or escalating.

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_terra_implementer
fork_turns: none
~~~

Its installed agent file pins GPT-5.6 Terra at max reasoning. Do not include a
per-spawn model or reasoning field. Confirm the public-details-first runtime evidence,
using the local inspector only when those details omit model or effort, before
accepting any work; if it is unavailable or differs, stop the lane rather than falling
back.

### Routing rules

- Route by task shape, not prestige.
- Apply the frontend, backend, or full-stack verification profile from the execution
  graph reference when that domain is material.
- Treat studio-approved design sources as immutable implementation contracts. If a
  material design decision is missing or conflicting, stop and ask the studio; do not
  let any model decide it.
- Use one worker per owned file set or bounded responsibility.
- State that the worker is not alone in the codebase, must preserve other edits, and
  must adapt to concurrent changes.
- Run independent, non-overlapping tasks concurrently when useful. Keep shared-file
  edits and dependency chains serial.
- Do not let parallel workers independently invent a shared interface. Settle a contract
  node first, then integrate against that accepted contract.
- Do not silently substitute a role, model, or reasoning level. If a requested lane is
  unavailable, report the limitation and ask before changing lanes.
- Give a failed lane a corrected spec. Do not repeat an unchanged prompt.

## Verify every implementation

Treat worker reports as claims. Before accepting work:

1. Inspect the working tree and actual diff.
2. Confirm only in-scope files changed.
3. Rerun the spec's verification commands in the primary session.
4. Compare the evidence with the stated objective and interfaces.
5. Delegate corrections when evidence fails or the diff is wrong.
6. Ensure the execution ledger contains the worker evidence and successful verification
   records before spawning the final reviewer.
7. For a graph, update the node state and invalidate descendant evidence when an
   upstream interface or base changes.

Do not call a task complete because a worker says it is complete.

## Consult Sol at commitment boundaries

Before committing to a consequential architecture, migration, public API, or wide
refactor, spawn a fresh custom review thread with a requested read-only profile:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

Use the commitment-boundary prompt from the role contracts. The installed agent file
pins Sol at high reasoning and requests a read-only sandbox; do not add a per-spawn
model or reasoning field. Observe the actual host sandbox and permission profile using
the same public-details-first procedure. Keep the consult bounded; the primary session
still makes the decision. If the mandatory preflight or runtime observation fails, stop
the consult instead of using a different reviewer.

## Require the final Sol review

After implementation and primary verification, always spawn a new, fresh native
custom review thread with:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

Give it the final-review packet from the role-contract reference. The reviewer is
role-pinned by its installed file, which requests read-only isolation. Instruct it to
remain behaviorally read-only, inspect the actual files and diff, then return exactly
one verdict: ship, fix-first, or rethink.

For independently accepted PR nodes, require a fresh review per PR. After a stacked or
cross-domain graph is integrated, require a final integration review when combined
behavior can fail despite individual node approval.

- ship: report completion with verification evidence.
- fix-first: delegate the named fixes, independently verify them, then obtain a new
  fresh review.
- rethink: return to architecture, revise the plan, and do not report completion.

For `ship`, record the review in the execution ledger and run its `accept` command. A
reviewer report alone is not an acceptance artifact.

Never waive the final review because the change is small. Never let the reviewer
implement its own fixes. A Sol-on-Sol review is context-clean, not
model-family-independent; describe it that way when independence matters.

Use the observed sandbox policy type to decide isolation status:

- If it is read-only, isolation is enforced and the review may proceed normally.
- If the host broadens it, the review may proceed only when the user and task do not
  require hard isolation, the review prompt explicitly forbids edits, and the parent
  captures and verifies exact before-and-after repository and artifact state. Report
  the broader observed sandbox and permission profile as residual risk.
- If hard isolation is required, the sandbox is unobservable, or any mutation occurs,
  stop the review lane. Do not claim read-only isolation and do not silently repair or
  hide the mutation.
