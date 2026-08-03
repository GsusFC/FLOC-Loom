# Native Codex role contracts

Use these contracts with FLOC*Loom's namespaced, role-pinned native custom agents.
They are not nested Codex CLI wrappers and they do not change global default-subagent
routing. Load only the contract needed for the next spawn. Adapt every placeholder;
do not remove a required field.

## Required custom-agent preflight

Before every spawn, complete steps 1–2 of the preflight in SKILL.md; complete steps
3–4 after spawn and before accepting the lane's result:

1. Resolve ../../scripts/install-agents.sh relative to SKILL.md and require its
   non-mutating --check to confirm all installed role files exactly match the shipped
   templates.
2. Require the native spawn tool to expose all three named custom agent types.
3. After spawn, inspect public native spawn/details metadata first. If it omits model
   or effort and the local rollout is accessible, resolve
   ../../scripts/inspect-agent-runtime.sh relative to SKILL.md and run it with the
   native subagent thread id plus the expected role/model/effort flags. Its allowlisted
   JSON is the authoritative local fallback for omitted model and effort. Public and
   local values must agree when both exist.
4. Require exact role, model, and reasoning-effort observation before accepting the
   selected lane. Always inspect and report the Sol reviewer's observed sandbox policy
   type and permission profile type; the shipped TOML requests read-only but a host may
   broaden it. The local fallback must reject missing sandbox or permission metadata.

A missing role file stops the current lane but may be installed through SKILL.md's
approval-gated first-use flow; after installation, require a fresh Codex task before
delegation. A stale, differing, conflicting, unavailable, inconsistent, or unobservable
role/model/effort also stops the affected lane and must not be overwritten or bypassed.
Report the actionable installer, local runtime-inspection, or fresh-task step; never
silently fall back to a built-in role, another model, another effort, or a differently
named agent. The custom-agent TOML pins the role's model and effort, so omit all
per-spawn model and reasoning overrides.

## Shared implementation contract

Every Luna or Terra prompt must contain the routing headers and all five implementation
sections below. Give each worker a non-overlapping file set or bounded responsibility.
Independent, non-overlapping work may run in parallel; shared files and dependency
chains must run serially. For a graph node, apply the lane and domain eligibility rules
in [execution-graphs.md](execution-graphs.md).

~~~text
ROUTING CONTEXT
GRAPH NODE: <stable node id, or direct>
DOMAIN: frontend | backend | full-stack | data | infrastructure | general
DELIVERY BOUNDARY: task | commit | PR
DEPENDS ON: <accepted node ids or none>
DESIGN SOURCE: <studio-approved reference/specification, or not applicable>
LANE REASON: <why Luna is the bounded first choice, or why Terra escalation is required>

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

The primary session must inspect the actual diff and rerun verification. The report is
not evidence by itself.

## Execution ledger

The parent session must create an execution ledger with `../../scripts/ledger.py` and
record each worker's observed routing, every successful verification command, the
before/after review snapshots, and the final review. The ledger's `accept` command is
the acceptance gate; a worker report or `VERDICT: ship` line by itself is insufficient.

The ledger stores artifacts outside the repository by default under
`$FLOC_LOOM_RUNS_DIR`, `$CODEX_HOME/floc-loom/runs`, or `$HOME/.codex/floc-loom/runs`.
Use an explicit `--ledger-root` for disposable tests. Its default policy requires an
observed reviewer sandbox type of `read-only`. If hard isolation is not required and
the host broadens the sandbox, acceptance must explicitly use
`--allow-behavioral-read-only` and report the residual risk.

## Luna — preferred bounded implementer

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_luna_implementer
fork_turns: none
~~~

The installed floc_loom_luna_implementer file pins GPT-5.6 Luna at max reasoning.
Do not attach a per-spawn model or reasoning field. Require public-details-first
runtime observation of that role and pin, using the local inspector only if public
details omit model or effort, before accepting its report.

Use Luna first for bounded frontend, backend, and full-stack nodes when the eligibility
conditions in `execution-graphs.md` are satisfied. It may own feature implementation,
but it must not own unsettled design or architecture decisions. High-risk security,
migration, concurrency, distributed-effects, debugging, and broad integration work
must be escalated when it cannot be bounded safely. Prompt:

~~~text
ROLE
Act as the preferred bounded implementation worker. Implement the supplied frontend,
backend, or full-stack node within its settled architecture and interfaces, and apply
the assigned domain verification profile. Make local implementation decisions that are
consistent with the contract, but report unresolved architecture or unusually
high-risk technical judgment instead of improvising. If a material design decision is
missing or conflicting, stop and return it to the studio; do not invent or reinterpret
the design.

<paste and complete the Shared implementation contract>
~~~

If the exact template preflight, native type exposure, or runtime pin observation
fails, stop and report the limitation. Never silently fall back to another model or
reasoning level.

## Terra — capability and high-risk escalation implementer

Spawn a native custom subagent thread with exactly:

~~~text
agent_type: floc_loom_terra_implementer
fork_turns: none
~~~

The installed floc_loom_terra_implementer file pins GPT-5.6 Terra at max reasoning.
Do not attach a per-spawn model or reasoning field. Require public-details-first
runtime observation of that role and pin, using the local inspector only if public
details omit model or effort, before accepting its report.

Use Terra when a node needs broader context or unusually high-risk technical judgment,
or when Luna's verified attempt demonstrates a capability/context mismatch. Prompt:

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

If the exact template preflight, native type exposure, or runtime pin observation
fails, stop and report the limitation. Never silently fall back to another model or
reasoning level.

## Fresh Sol — requested-read-only final reviewer

Spawn a new native custom review thread after implementation and primary-session
verification, with exactly:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

The installed floc_loom_sol_reviewer file pins GPT-5.6 Sol at high reasoning and
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

VERIFICATION EVIDENCE
- <command> -> <actual primary-session output evidence>
- <Relevant artifact or diff inspection> -> <actual evidence>
- <Frontend browser evidence, backend boundary evidence, or full-stack integration
  evidence when applicable>

REVIEW
Inspect the actual files and accumulated change set. Judge correctness, completeness,
regressions, scope discipline, interface preservation, test adequacy, and material risk.
Return exactly one allowed verdict: ship, fix-first, or rethink.

SOL REVIEW
VERDICT: ship | fix-first | rethink
REASON: <decisive evidence-based reason>
FINDINGS: <precise file references and required fixes, or none>
RESIDUAL RISK: <most important remaining risk, or none>
~~~

Use ship only when the stated goal is met by the inspected change set and evidence.
Use fix-first for bounded required corrections. Use rethink when architecture or scope
must change. If any fix is made after review, discard that verdict and run a new,
fresh reviewer under the same observed-sandbox policy with a newly accumulated change
set and verification evidence. After a `ship` verdict, the parent must record it in
the execution ledger and run the fail-closed `accept` command before reporting done.

If the exact template preflight, native type exposure, or required role/model/effort
observation fails, stop and report the limitation. Never silently fall back to another
model or reasoning level. Sol reviewing Sol is context-clean, but it is not
cross-model-family independence.

Apply the observed sandbox policy, not the requested TOML value, to review acceptance:

- If the observed sandbox policy type is read-only, proceed with enforced isolation.
- If the host broadens it, proceed only when hard isolation is not required, this prompt
  forbids edits, and the parent captures and verifies exact before-and-after repository
  and artifact state. Include the broader sandbox and permission profile as residual
  risk in the review packet and final report.
- If hard isolation is required, the sandbox cannot be observed, or any mutation
  occurs, stop the lane. Do not claim enforced read-only isolation.

## Commitment-boundary Sol consult

For a pre-implementation consult, use a fresh native custom review thread with a
requested read-only profile, exactly:

~~~text
agent_type: floc_loom_sol_reviewer
fork_turns: none
~~~

Give it the proposed decision, stated goal, constraints, relevant paths, alternatives,
and the one question whose answer changes the plan. Require proceed, change, or stop,
followed by the decisive reason and largest risk. Apply the same exact-template,
native-exposure, public-details-first runtime-observation, sandbox-reporting, and
no-fallback rules as final review.
