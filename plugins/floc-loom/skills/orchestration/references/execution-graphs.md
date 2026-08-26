# Adaptive execution graphs

Use this reference when a deliverable spans multiple independently verifiable pieces,
crosses frontend/backend boundaries, requests stacked PRs, or can materially benefit
from parallel work. A single bounded change does not need a ceremonial graph. Read the
normative route policy in [SKILL.md](../SKILL.md) and command/evidence mechanics in
[operations.md](operations.md) before activating a node.

The graph represents delivery dependencies, not a promise to create a PR for every
node. Map a node to a task, commit, or PR according to review and rollback needs.
Never create branches, commits, or PRs unless the user has authorized those actions.

## Build the graph

Create a directed acyclic graph before spawning implementation workers. Each node must
use this shape:

~~~text
NODE
ID: <stable short id>
OUTCOME: <observable result>
DOMAIN: frontend | backend | full-stack | data | infrastructure | general
DELIVERY BOUNDARY: task | commit | PR
DEPENDS ON: <node ids or none>
OWNED FILES: <exact non-overlapping paths>
INTERFACES: <types, API contracts, schemas, events, assets, or none>
DESIGN SOURCE: <studio-approved reference/specification, or not applicable>
RISK: low | medium | high
ROUTE: solo | delegate | audit | full
LANE: none | Luna | Terra
VERIFICATION: <exact commands and observable evidence>
INTEGRATION: <consumer nodes and final integration checks>
STATUS: blocked | ready | active | verified | accepted
~~~

Reject a proposed graph when it contains a cycle, hides a shared mutable interface,
assigns overlapping files to concurrent nodes, omits a route, or lacks a final
integration node for changes whose behavior only emerges across boundaries.

## Choose the delivery boundary

- Use a **task** for a small change that will be reviewed and accepted with a larger
  accumulated diff.
- Use a **commit** when the result should remain independently understandable or
  revertible, but does not need separate external review.
- Use a **PR** when the result has its own review audience, rollout, risk boundary, or
  merge timing. An independently accepted PR uses `audit` or `full`.

For stacked PRs, record each PR's expected base. If an upstream PR changes after a
downstream node starts, rebase or update the descendant and rerun its verification.
Passing against an obsolete base is not acceptance evidence.

## Declare and compose routes

Read-only discovery and preflight may precede route declaration. Before a node's first
mutation or auxiliary spawn, record exactly one route for that node. The one-auxiliary
default is **per node**, not global: independent nodes can each use their own bounded
auxiliary when their file ownership does not overlap.

A node can only move to a stronger route; do not downgrade a node or carry a weaker
ledger forward. `solo` never has an auxiliary or ledger. `delegate` has one Luna worker
plus verified-state binding. `audit` has primary implementation/verification plus fresh
Sol review and no worker evidence. `full` has one Luna/Terra worker, primary
verification, and fresh Sol review. Use the ledger escalation command only for
non-solo nodes; see [operations.md](operations.md).

Integration nodes and independently accepted PR nodes must choose `audit` or `full`.
If a node reaches one of the conditional review-trigger surfaces defined in
[role-contracts.md](role-contracts.md#conditional-security-and-observability-sweep), it
must choose `audit` or `full`; if it delegates implementation, it must choose `full`.

## Route by capability

Luna Max is the preferred implementation lane for a `delegate` or `full` frontend or
backend node after Sol has settled architecture, design source, interfaces, ownership,
and acceptance criteria. Start with Luna when every condition below is true:

- The node has one bounded outcome and exact owned files or responsibility.
- The studio-approved design source and technical interfaces are settled.
- The specification states important behavior, invariants, and failure cases.
- Verification can detect material failure modes.
- The node does not require unresolved architecture or unusually high-risk judgment in
  security, migrations, concurrency, distributed effects, or broad integration.

Use Terra only on `full` before implementation when one condition is false or unknown.
If a Luna attempt exposes a correctable specification gap, Sol may correct the
specification and make one fresh Luna attempt. Escalate to Terra when the failure shows
a capability/context mismatch, or when the corrected Luna attempt also fails. Never
repeat an unchanged prompt.

An unsettled design decision is the exception: do not route it to Terra. Block the node
and return the decision to the studio.

## Schedule safe waves

A node is ready only when:

1. Every dependency is accepted, not merely reported complete.
2. Its interfaces, route, and required design source are settled.
3. Its owned files do not overlap another active node.
4. It does not mutate a shared schema, migration chain, lockfile, generated registry,
   design token source, or other serialization point concurrently.

Run ready, non-overlapping nodes concurrently when that reduces elapsed time. Run
shared-file edits and dependency chains serially. The primary session owns graph state,
inspects every diff, reruns every verification command, and updates node state.

Worker completion reports are claims. A node becomes `verified` only after primary
verification and `accepted` only after its selected route's review/ledger gate succeeds.

## Design authority

The studio owns visual and interaction design. Models implement and verify the accepted
design; they do not invent, improve, simplify, or reinterpret it without explicit
authorization.

Every material frontend node must identify its approved design source: Figma frame,
screenshot, prototype, design-system component, token set, motion specification, or
written state matrix. The source must define enough of the relevant layout, states,
responsive behavior, content, and motion to implement the node.

If sources conflict or leave a material visual decision open, stop the node and ask the
studio. Do not use Terra as a substitute design authority. Any intentional visual
deviation must be listed and approved before implementation continues.

## Frontend profile

Frontend nodes must define target routes, components, states, and viewport range.
Verification should include, where relevant:

- Type checking, linting, unit/component tests, and production build.
- Real-browser interaction for primary flows and error/empty/loading states.
- Desktop and mobile viewport evidence.
- Browser console and failed-network-request inspection.
- Keyboard navigation, visible focus, labels, and basic accessibility checks.
- Screenshot or visual evidence against the studio-approved reference.

If browser execution is unavailable, report visual QA as missing. A build passing is
not evidence that layout, interaction, responsiveness, or accessibility is correct.

## Backend profile

Backend nodes must identify the public contract, persistence effects, trust boundary,
and rollback behavior. Verification should include, where relevant:

- Unit and integration tests at the real API or service boundary.
- Request/response schema and backward-compatibility checks.
- Authentication, authorization, tenant isolation, validation, and error behavior.
- Transaction, idempotency, concurrency, retry, and duplicate-delivery behavior.
- Migration forward-path plus rollback or documented restore strategy.
- Observability without leaking secrets or customer data.

## Full-stack profile

Do not let frontend and backend workers independently invent the same interface. Create
or nominate a contract node first. It owns the shared schema, API shape, event, or
types and must be accepted before dependent implementation starts, unless the interface
is already stable and versioned. Treat the studio-approved design source as a separate
immutable frontend contract; technical interface ownership does not confer design
authority.

Once the contract is settled, frontend and backend nodes may run in parallel when their
file ownership does not overlap. The integration node may use Luna only when bounded by
the accepted contract and complete end-to-end verification; otherwise route it to Terra
on `full`. Always exercise the real boundary, including at least one success path and
material failure paths.

## Review and ledger boundaries

Use one ledger per direct deliverable or graph node. A larger graph may have several
ledgers because its route declarations compose; do not accumulate unrelated nodes into
a reviewer-free acceptance path. Use separate ledgers for independently accepted PRs.

For each node:

- Record the declared route before work and record any monotonic escalation explicitly.
- Capture primary verification evidence for every non-solo route.
- On `delegate`, bind successful verification to the unchanged verified state.
- On `audit` and `full`, capture the fresh review's before/after state and required
  non-sensitive coverage evidence.
- After all nodes are integrated, rerun the complete verification suite and obtain an
  audit/full final integration review when cross-node behavior or a stacked chain can
  fail despite individual node approval.

Do not merge `ship` verdicts mechanically. An upstream correction invalidates affected
downstream evidence and requires re-verification and, when the reviewed diff changed, a
fresh review.

## Learn from routing outcomes

Do not settle Luna-versus-Terra routing through anecdotes. Periodically compare nodes by
domain and initial classification using observable evidence:

- first-pass verification success;
- correction and escalation count;
- reviewer verdict;
- scope violations or regressions;
- elapsed time and usage when the runtime exposes them.

Keep Luna-first routing where it preserves required quality. Tighten the node boundary
or route that class to Terra when evidence shows repeated corrections, regressions, or
failed reviews.
