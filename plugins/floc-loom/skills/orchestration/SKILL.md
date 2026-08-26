---
name: orchestration
description: "Codex-native architect, setup, and delegation workflow that uses separately installed, role-pinned custom agents: GPT-5.6 Luna at max reasoning for bounded implementation, GPT-5.6 Terra at max reasoning for high-risk escalation, and a fresh GPT-5.6 Sol reviewer with observed sandbox evidence. Use for FLOC*Loom installation or onboarding, selective solo/delegate/audit/full routing, adaptive execution graphs, frontend/backend/full-stack work, execution-ledger evidence, commitment-boundary advice, or final review before acceptance."
---

# FLOC*Loom Orchestration

Act as the architect. Own the user's intent, architecture, route declaration,
dependency graph, verification, and final acceptance. Use the least expensive route
that still supplies the guarantees the task needs; lower cost is never proof of lower
risk. Native custom-agent threads are not nested Codex CLI wrappers or a global
subagent default.

**Mandatory reads before work:**

1. Read [references/role-contracts.md](references/role-contracts.md) before the first
   delegation, commitment consult, or final review. It defines role pins, review
   packets, the semantic security/observability sweep, and correction-boundary rules.
2. Read [references/operations.md](references/operations.md) before the first route
   declaration, runtime observation, ledger operation, installer update, or acceptance.
   It owns commands, evidence capture, ledger mechanics, and maintenance details.
3. Read [references/execution-graphs.md](references/execution-graphs.md) before
   planning a multi-deliverable, parallel, stacked-PR, frontend/backend, or full-stack
   build. It defines graph composition, safe scheduling, lane eligibility, domain
   verification, and integration acceptance.

## Confirm the primary session

Run the primary Codex session on GPT-5.6 Sol with high reasoning. Verify the current
model and effort when the runtime exposes them. If either setting differs, tell the
user how to select Sol / High and stop before delegation. If the runtime does not
expose the settings, ask the user to confirm Sol / High and stop until they confirm. A
skill cannot change the primary session's model itself; never assume or claim this
prerequisite is satisfied.

## Preflight the companion custom agents

The three role files are user-owned native custom-agent TOML files. Installing or
updating this plugin does **not** register them automatically. They must be installed
separately and a fresh Codex task must be started so the native spawn tool can discover
the current roles.

Before every delegation, run the role-aware non-mutating check from the directory
containing this SKILL.md. Follow the exact commands and migration exits in
[operations.md](references/operations.md). The all-role `--check` remains the default
preflight; `--check-role luna|terra|sol` narrows a deliberate role-specific check.

The check proves installed role files match the current shipped templates. Missing files
may be added only through the approval-gated installer flow. A stale, differing,
symlinked, or conflicting file is a deliberate refusal: do not overwrite it, select a
substitute role, or work around it. The v0.5 installer may migrate only an allowlisted,
byte-exact historical shipped Sol reviewer; it never overwrites arbitrary user changes.
After any successful role install or migration, stop and ask the user to start a fresh
Codex task because native role discovery occurs at task creation.

Inspect the native spawn tool's available `agent_type` entries before any lane runs.
All three names must be exposed exactly:

- `floc_loom_luna_implementer`
- `floc_loom_terra_implementer`
- `floc_loom_sol_reviewer`

After spawn, accept lane routing only after the public-details-first/runtime-inspector
procedure from the role contracts proves the selected role, model, and effort. The
reviewer additionally requires observed sandbox policy type and permission profile
type. If a value is absent, inconsistent, unavailable, or unobservable, stop that lane
with its executable installer/fresh-task/runtime-inspection exit. Never silently fall
back to another role, model, or effort. The custom-agent file—not the spawn call—pins
each model and reasoning effort.

## Declare a selective route before work

Read-only discovery and role preflight may precede route selection. For every direct
deliverable or graph node, declare **one** route before its first mutation or auxiliary
spawn. The declaration is scoped to that deliverable/node, not globally: an adaptive
graph may safely compose several independently routed nodes. Persist every non-solo
route in its route-aware ledger before work; record a solo route in the direct spec or
graph node.

Routes may only escalate. Never downgrade a declaration or reuse a weaker ledger after
a task crosses its boundary. Use the explicit ledger escalation operation from
[operations.md](references/operations.md) for `delegate`/`audit`/`full`; reclassify
`solo` before exceeding its boundary.

| Route | Use only when | Acceptance contract |
|---|---|---|
| `solo` | Read-only work, or one-file mechanical low-risk mutation | No auxiliary and no delegated-deliverable ledger; reclassify first if the boundary expands |
| `delegate` | One bounded Luna implementer can substitute for primary implementation | Root verification plus the exact unchanged verified-state binding; no Sol review and no Terra |
| `audit` | Primary session implements and verifies, then needs independent review | Successful primary verification and one fresh Sol review; worker evidence is rejected |
| `full` | A Luna/Terra implementer is justified and independent review remains required | One worker, root verification, and one fresh Sol review |

Consequential integration boundaries and independently accepted PR boundaries require
`audit` or `full`. The one-auxiliary default is per direct deliverable/node, never a
cap on unrelated graph nodes. `delegate` has exactly one bounded Luna implementation
worker; risk-driven Terra evidence is accepted only on `full`.

Any work that touches a conditional review-trigger surface defined in
[role-contracts.md](references/role-contracts.md#conditional-security-and-observability-sweep)
must use `audit` or `full` so the required final-review sweep cannot be bypassed. When
an implementer is used on that work, route `full`. Do not turn a sensitive task into
`solo` or reviewer-free `delegate` by splitting it into symptom patches.

## Choose direct execution or an adaptive graph

Use a direct five-part implementation spec for one bounded, independently verifiable
change. Do not create graph ceremony when there is no useful dependency or concurrency
decision.

For two or more material deliverables, cross-domain work, parallel execution, or
stacked PRs, build the adaptive execution graph before delegation. The graph is a
delivery DAG, not automatically a PR graph: choose a task, commit, or PR boundary
according to review and rollback needs. Branch, commit, and PR creation still require
the user's authorization.

The primary session owns graph state. Start a node only when dependencies are accepted,
interfaces are settled, its route is declared, and its file ownership does not overlap
another active node. Add an integration node whenever correctness emerges across nodes
or frontend/backend boundaries. Worker reports do not advance a node to verified or
accepted without primary evidence and the route's required gate.

## Keep architect work in the primary session

Keep these responsibilities in the primary session:

- Resolve requirements and material ambiguity.
- Choose architecture, interfaces, delivery boundary, and route.
- Write the complete five-part spec and graph node contract.
- Inspect the actual diff and rerun verification.
- Capture the required ledger evidence and judge reviewer feedback.
- Accept only after the route's machine-checked gate succeeds.

Do not type implementation code, tests, boilerplate, or mechanical configuration in the
primary session when the selected route delegates that responsibility. If a lane result
is wrong, correct the specification and delegate the correction rather than silently
repairing it.

## Route implementation lanes

### Luna: preferred bounded implementation lane

Use Luna Max for a `delegate` or `full` node after Sol has settled architecture,
interfaces, ownership, constraints, and verification. Luna may own coherent feature
implementation; it is not limited to boilerplate. Do not route unsettled design or
architecture decisions to Luna. After a failed Luna attempt, inspect evidence: correct
a genuine specification gap and allow one fresh Luna attempt, or escalate when the
failure shows a capability/context mismatch. Escalate after a corrected Luna attempt
also fails.

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_luna_implementer
fork_turns: none
~~~

The installed file pins GPT-5.6 Luna at max reasoning. Do not include per-spawn model
or reasoning fields. Confirm accepted routing evidence before accepting its work.

### Terra: capability and high-risk escalation lane

Use Terra only on `full` when a node cannot be bounded reliably for Luna or correctness
depends on unusually broad context or technical judgment: subtle security, migration,
concurrency, distributed effects, difficult production debugging, broad refactors, or
large cross-module integration. Terra is not a design authority. If design is
unsettled, stop and return the decision to the studio.

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_terra_implementer
fork_turns: none
~~~

The installed file pins GPT-5.6 Terra at max reasoning. Do not include per-spawn model
or reasoning fields. Confirm accepted routing evidence before accepting its work.

### Common lane rules

- Route by task shape and declared guarantees, not prestige.
- Apply the frontend, backend, or full-stack verification profile from the execution
  graph reference when that domain is material.
- Treat studio-approved design sources as immutable implementation contracts. If a
  material design decision is missing or conflicting, stop and ask the studio; no model
  may invent, improve, simplify, or reinterpret it.
- State worker ownership exactly. Workers are not alone in the codebase; they must
  preserve concurrent edits and adapt to already-present changes.
- Run independent non-overlapping nodes concurrently only after shared contracts are
  settled. Keep shared-file edits and dependency chains serial.
- Do not let parallel workers invent a shared interface. Settle a contract node first,
  then integrate against that accepted contract.
- Do not silently substitute a role, model, effort, route, or verification profile.

## Verify and accept every implementation

Treat reports as claims. Before acceptance, inspect the working tree and actual diff,
confirm only in-scope files changed, rerun the route's verification commands, and
compare evidence with the objective and interfaces. Run source-mutating normalizers
before functional verification. Corrections require fresh verification; changed reviewed
diffs require fresh review evidence.

For `delegate`, acceptance requires the Luna worker evidence, successful verification,
and the exact unchanged verified-state binding. For `audit`, primary implementation has
no worker evidence and acceptance requires fresh Sol review. For `full`, acceptance
requires one worker plus fresh Sol review. `solo` is outside the ledger and must be
reclassified before it requires an auxiliary or broader mutation.

For an `audit` or `full` final review, use the role-contract final-review packet. It
applies the conditional security/observability sweep, non-sensitive `COVERAGE`, and
one-bundle/then-`rethink` rule when triggered. Keep commitment-boundary consultation
separate: it returns `proceed`, `change`, or `stop` and does not inherit unrelated final
review coverage.

Spawn that fresh final review thread with exactly:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

The installed reviewer file pins GPT-5.6 Sol at high reasoning. Do not add per-spawn
model or reasoning fields; accept its routing only after the observed role/pin/sandbox
procedure in the role contracts succeeds.

Do not report completion until the route's ledger `accept` gate succeeds (or, for a
true solo route, the primary session records and verifies its no-ledger boundary). A
Sol-on-Sol review is context-clean, not model-family-independent; say so when
independence matters.
