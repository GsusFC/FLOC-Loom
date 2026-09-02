# Native Codex role contracts

Use these contracts with FLOC*Loom's namespaced, role-pinned native custom agents.
They are not nested Codex CLI wrappers and do not change global default-subagent
routing. Read this reference before the first delegation or final review in a session.
The route policy itself lives in [SKILL.md](../SKILL.md); commands and evidence capture
live in [operations.md](operations.md).

## Required custom-agent preflight

Before every spawn, complete the installed-agent exactness preflight, confirm that all
three custom agent types are exposed, and observe the selected lane's actual routing
metadata. Use public native spawn/details metadata first. If it omits model or effort
and the local rollout is accessible, resolve `../../scripts/inspect-agent-runtime.sh`
relative to SKILL.md and use its allowlisted JSON with expected role/model/effort
flags. Public and local values must agree when both exist.

Require the following observations before accepting a lane result:

| Lane | Role | Model / effort | Additional observation |
|---|---|---|---|
| Bounded implementation | `floc_loom_luna_implementer` | GPT-5.6 Luna / max | Exact role pin |
| Escalated implementation | `floc_loom_terra_implementer` | GPT-5.6 Terra / max | Exact role pin |
| Fresh review | `floc_loom_sol_reviewer` | GPT-5.6 Sol / high | Sandbox policy type and permission profile type |

The shipped reviewer TOML requests read-only isolation, but the request is not proof
that the host enforced it. A missing, stale, differing, symlinked, conflicting,
unavailable, inconsistent, or unobservable role/model/effort stops the affected lane.
Never silently fall back to a built-in role, another model, another effort, or a
differently named agent. The custom-agent TOML pins model and effort, so omit
per-spawn model and reasoning overrides.

## Shared implementation contract

Every Luna or Terra prompt must contain the route headers and all five implementation
sections below. Give each worker a non-overlapping file set or bounded responsibility.
Independent, non-overlapping work may run in parallel; shared files and dependency
chains must run serially. For a graph node, apply the lane and domain eligibility rules
in [execution-graphs.md](execution-graphs.md).

~~~text
ROUTING CONTEXT
GRAPH NODE: <stable node id, or direct>
ROUTE: delegate | full
DOMAIN: frontend | backend | full-stack | data | infrastructure | general
DELIVERY BOUNDARY: task | commit | PR
DEPENDS ON: <accepted node ids or none>
DESIGN SOURCE: <studio-approved reference/specification, or not applicable>
LANE REASON: <why Luna is the bounded first choice, or why Terra escalation is required>

MINIMAL-CHANGE BASIS
OBSERVED FAILURE OR INVARIANT: <concrete behavior to restore or preserve>
EXISTING MECHANISM INSPECTED: <closest current path, or none with evidence>
SEMANTICS AND INTERFACES TO PRESERVE: <current behavior that must not change>
AUTHORIZED ARCHITECTURAL EXPANSION: none | <exact approved addition>
NON-GOALS: <adjacent concurrency, scaling, migration, compatibility, or other excluded work>

OBJECTIVE
<Observable outcome and why it matters.>

FILES AND OWNERSHIP
You own only:
- <exact file or module>

You are not alone in the codebase. Other agents or the user may be editing concurrently.
Preserve their edits, do not revert unrelated work, and adapt to changes already present.
Do not modify files outside your ownership.

INTERFACES
- <Signatures, types, schemas, commands, or behavior that must remain compatible.>

CONSTRAINTS
- <Repository conventions, safety boundaries, excluded scope, and settled decisions.>

VERIFICATION
- Run: <exact command>
  Success: <concrete expected result>
- Inspect: <exact file, diff, or generated artifact>
  Success: <concrete expected evidence>
- Domain gate: <browser evidence, API/integration evidence, or not applicable>
  Success: <observable domain-specific evidence>

RETURN
Return the report below. Include exact commands and actual output evidence; a completion
claim without evidence is invalid.

IMPLEMENTATION REPORT
STATUS: complete | partial | blocked
GRAPH NODE: <stable node id, or direct>
DOMAIN: <assigned domain>
OBJECTIVE: <one-line restatement>
CHANGES: <file-by-file summary from the actual diff>
VERIFIED: <exact commands plus concrete output evidence>
JUDGMENT CALLS: <decisions the spec left open, or none>
GAPS: <unfinished work, ambiguity, or none>
~~~

`delegate` may use only the bounded Luna lane. `full` may use one Luna or Terra lane.
Do not send a worker on `solo` or `audit`: solo has no auxiliary, while audit means the
primary session implements and verifies before a fresh Sol review.

The worker must inspect the named existing mechanism before editing. Reuse means its
current path and semantics; it does not authorize extending, wrapping, versioning,
duplicating, or bypassing it. When `AUTHORIZED ARCHITECTURAL EXPANSION` is `none`, any
new contract, schema/version, migration, index, adapter, service, lock, or durable state
is out of scope. Stop and report evidence when the supplied boundary is insufficient.

## Execution ledger

The parent session declares a ledger route before its first mutation or auxiliary spawn
for the direct deliverable or graph node. It records the route immutably at `init`; an
explicit command may only escalate it. The ledger's `accept` command is the acceptance
gate, not a worker report or a `VERDICT: ship` line. Follow the exact procedures in
[operations.md](operations.md).

The evidence matrices are strict:

| Active route | Required evidence at acceptance | Forbidden evidence |
|---|---|---|
| `delegate` | One Luna worker, successful verification, and unchanged verified-state binding | Sol review, Terra worker |
| `audit` | Successful primary verification and fresh Sol review | Worker evidence |
| `full` | One Luna or Terra worker, successful primary verification, and fresh Sol review | Extra workers |

The ledger stores artifacts outside the repository by default under
`$FLOC_LOOM_RUNS_DIR`, `$CODEX_HOME/floc-loom/runs`, or `$HOME/.codex/floc-loom/runs`.
It rejects a missing route, downgrade, changed evidence file, changed verified state,
changed review state, out-of-scope file, wrong role pin, or incomplete evidence matrix.

## Luna — preferred bounded implementer

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_luna_implementer
fork_turns: none
~~~

The installed `floc_loom_luna_implementer` file pins GPT-5.6 Luna at max reasoning.
Do not attach a per-spawn model or reasoning field. Require public-details-first runtime
observation of that role and pin, using the local inspector only if public details omit
model or effort, before accepting its report.

Use Luna only when the route and eligibility conditions allow it. It may own coherent
feature implementation, but it must not own unsettled design or architecture decisions.
Prompt:

~~~text
ROLE
Act as the preferred bounded implementation worker. Implement the supplied frontend,
backend, or full-stack node within its settled architecture and interfaces, and apply
the assigned domain verification profile. Make local implementation decisions that are
consistent with the contract, but report unresolved architecture or unusually high-risk
technical judgment instead of improvising. If a material design decision is missing or
conflicting, stop and return it to the studio; do not invent or reinterpret the design.

<paste and complete the Shared implementation contract>
~~~

## Terra — capability and high-risk escalation implementer

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_terra_implementer
fork_turns: none
~~~

The installed `floc_loom_terra_implementer` file pins GPT-5.6 Terra at max reasoning.
Do not attach a per-spawn model or reasoning field. Require public-details-first runtime
observation of that role and pin, using the local inspector only if public details omit
model or effort, before accepting its report.

Use Terra only on `full` when a node needs broad context or unusually high-risk
technical judgment, or when Luna's verified attempt demonstrates a capability/context
mismatch. Prompt:

~~~text
ROLE
Act as the product implementation worker. Resolve implementation details within the
settled architecture, apply the assigned domain verification profile, document material
technical judgment calls, and preserve every stated interface and constraint. Implement
frontend only against the supplied studio-approved design source. If that source leaves
a material decision open or conflicts with another source, stop and return it to the
studio; do not redesign.

<paste and complete the Shared implementation contract>
~~~

## Conditional security and observability sweep

This section is the semantic source for the final-review sweep. It applies only to an
`audit` or `full` **final** review when the reviewed change or stated work contains any
of these triggers:

- provider/client I/O;
- logging or telemetry;
- exception handling;
- schemas or serialization;
- configuration;
- URLs or credentials; or
- transport debugging.

When triggered, inspect all of the following categories across the accumulated change
set, not just the line that first looked risky:

1. Ingress, parsing, validation, and serialization.
2. Success, exception, fallback, cache, and early-return control flow.
3. Application logs, failure records, usage observations, summaries, and transport/debug sinks.
4. Configuration-derived endpoint and URL metadata.
5. Stale state across sequential calls plus safe/default transitions.

### Exact machine coverage schema

This section remains the semantic authority for the sweep. The single public source for
the exact trigger/category identifiers and compact artifact fields is the deterministic
`coverage-schema --json` document from the shipped ledger; resolve and invoke it through
[operations.md](operations.md). Do not infer or hand-copy IDs from
implementation internals. The verifier binds that document to this semantic source.

Machine coverage schema fingerprint: `sha256:d4f99799e07e9ced79242175d6d17d2a1c3394faf583554c831b92aaaa6b8a21`

The final-review packet must identify whether the sweep was triggered. The reviewer
must return a `COVERAGE` section that lists the triggers, categories inspected, and a
justified exclusion for every category not inspected. `COVERAGE` must never include
payloads, complete URLs, credentials, bodies, prompt content, tokens, environment
values, or configuration values. The ledger accepts the matching compact structured
coverage artifact described in [operations.md](operations.md), not free-form sensitive
runtime data.

### One correction bundle per review boundary

A final-review packet names a direct deliverable/node and `REVIEW CYCLE: initial` or
`post-fix-first-bundle`. On the initial cycle, `fix-first` must group **every known
blocker from this sweep at that review boundary** into one correction bundle. The parent
independently verifies that bundle, then obtains a fresh review with
`REVIEW CYCLE: post-fix-first-bundle`.

If that fresh post-bundle review finds another blocker, it returns `rethink`, not a
second automatic patch cycle. This is not loop-until-clean behavior. Scope the single
bundle to the direct deliverable/node/review boundary; never consume a global budget.
The ledger intentionally does not add a correction-count state machine: the review
packet and fresh reviewer make the boundary explicit.

## Fresh Sol — requested-read-only final reviewer

Spawn a new native custom review thread after the required implementation/primary
verification, with exactly:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

The installed `floc_loom_sol_reviewer` file pins GPT-5.6 Sol at high reasoning and
requests a read-only sandbox. Do not attach a per-spawn model or reasoning field.
Require public-details-first observation of the Sol/high pin, using the local inspector
only if public details omit model or effort. Also capture the observed sandbox policy
type and permission profile type; the requested profile does not prove host-enforced
read-only isolation.

Prompt:

~~~text
ROLE
Act as the fresh final reviewer. Remain strictly read-only: do not edit files, implement
fixes, or broaden scope.

ROUTE AND REVIEW BOUNDARY
ROUTE: audit | full
REVIEW BOUNDARY: <direct deliverable or stable node id>
REVIEW CYCLE: initial | post-fix-first-bundle

STATED GOAL
<The user's requested outcome.>

ACCUMULATED CHANGE SET
<Exact allowed files plus the complete working-tree diff, or explicit base/head revisions.>

GRAPH AND INTEGRATION
<Node id and accepted dependencies, or direct. For an integration review, include the
complete graph, PR bases, invalidated/reverified descendants, and final integration
node evidence.>

INTERFACES AND CONSTRAINTS
- <Required compatibility, repository rules, safety boundaries, and excluded scope.>
- <Studio-approved design source and approved deviations, or not applicable.>

MINIMAL-CHANGE BASIS
OBSERVED FAILURE OR INVARIANT: <the behavior the change was required to restore or preserve>
EXISTING MECHANISM INSPECTED: <the current path examined before design>
SEMANTICS AND INTERFACES TO PRESERVE: <the unchanged contract>
AUTHORIZED ARCHITECTURAL EXPANSION: none | <exact approved addition>
NON-GOALS: <explicitly excluded adjacent concerns>

VERIFICATION EVIDENCE
- <command> -> <actual primary-session output evidence>
- <Relevant artifact or diff inspection> -> <actual evidence>
- <Frontend browser evidence, backend boundary evidence, or full-stack integration
  evidence when applicable>

CONDITIONAL SECURITY/OBSERVABILITY SWEEP
<Applicable trigger(s), or "not triggered; no listed surface is in scope">.

REVIEW
Inspect the actual files and accumulated change set. Judge correctness, completeness,
regressions, scope discipline, interface preservation, test adequacy, material risk,
whether the existing mechanism was inspected before design, and whether the diff adds
unapproved architectural surface or changes reused semantics. Apply the conditional
sweep when it is triggered. Return exactly one allowed verdict.

SOL REVIEW
VERDICT: ship | fix-first | rethink
REASON: <decisive evidence-based reason>
FINDINGS: <precise file references and required fixes, or none>
COVERAGE:
TRIGGERS: <identifiers from the public coverage schema, or none>
INSPECTED: <categories from the public coverage schema, or none>
EXCLUSIONS:
- <public coverage-schema category> — <short non-sensitive justification>
RESIDUAL RISK: <most important remaining risk, or none>
~~~

Use `ship` only when the stated goal is met by the inspected change set and evidence.
Use `fix-first` only for the one bounded correction bundle described above. Use
`rethink` when architecture/scope must change or a post-bundle review finds another
blocker. After a `ship` verdict, record it in the execution ledger and run the
fail-closed `accept` command before reporting done.

Apply the observed sandbox policy, not the requested TOML value, to review acceptance:

- If the observed sandbox policy type is `read-only`, proceed with enforced isolation.
- If the host broadens it, proceed only when hard isolation is not required, this prompt
  forbids edits, and the parent captures and verifies exact before-and-after repository
  and artifact state. Include the broader sandbox and permission profile as residual
  risk in the review packet and final report.
- If hard isolation is required, the sandbox cannot be observed, or any mutation
  occurs, stop the lane. Do not claim enforced read-only isolation.

## Commitment-boundary Sol consult

For a pre-implementation consult, use a fresh native custom review thread with the
same role pin and requested read-only profile:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

Give it the proposed decision, stated goal, constraints, relevant paths, the existing
mechanism inspected, evidence for any requested architectural expansion, alternatives,
and the one question whose answer changes the plan. Require exactly `proceed`,
`change`, or `stop`, followed by the decisive reason and largest risk. This is not a
final review: do **not** require or invent final-review `COVERAGE` for an unrelated
commitment-boundary consult. Apply the same exact-template, native-exposure,
public-details-first runtime-observation, sandbox-reporting, and no-fallback rules.
