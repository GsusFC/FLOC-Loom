# Adaptive execution graphs

Use this reference when a deliverable spans multiple independently verifiable pieces,
crosses frontend/backend boundaries, requests stacked PRs, or can materially benefit
from parallel work. A single bounded change does not need a ceremonial graph.

The graph represents delivery dependencies, not a promise to create a PR for every
node. Map a node to a task, commit, or PR according to its review and rollback needs.
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
LANE: Luna | Terra
VERIFICATION: <exact commands and observable evidence>
INTEGRATION: <consumer nodes and final integration checks>
STATUS: blocked | ready | active | verified | accepted
~~~

Reject a proposed graph when it contains a cycle, hides a shared mutable interface,
assigns overlapping files to concurrent nodes, or lacks a final integration node for
changes whose behavior only emerges across boundaries.

## Choose the delivery boundary

- Use a **task** for a small change that will be reviewed and accepted with a larger
  accumulated diff.
- Use a **commit** when the result should remain independently understandable or
  revertible, but does not need separate external review.
- Use a **PR** when the result has its own review audience, rollout, risk boundary, or
  merge timing.

For stacked PRs, record each PR's expected base. If an upstream PR changes after a
downstream node starts, rebase or update the descendant and rerun its verification.
Passing against an obsolete base is not acceptance evidence.

## Route by capability

Luna Max is the preferred implementation lane for frontend and backend nodes after Sol
has settled the architecture, design source, interfaces, ownership, and acceptance
criteria. This includes bounded feature implementation, not only mechanical edits.
Start with Luna when every condition below is true:

- The node has one bounded outcome and exact owned files or responsibility.
- The studio-approved design source and technical interfaces are settled.
- The specification states the important behavior, invariants, and failure cases.
- Verification can detect the material ways the node could be wrong.
- The node does not require unresolved architecture or unusually high-risk judgment in
  security, migrations, concurrency, distributed effects, or broad cross-module
  integration.

Use Terra before implementation when one of those conditions is false or unknown. If a
Luna attempt exposes a correctable specification gap, Sol may correct the specification
and make one fresh Luna attempt. Escalate to Terra when the failure shows a capability
or context mismatch, or when the corrected Luna attempt also fails. Never repeat an
unchanged prompt.

An unsettled design decision is the exception: do not route it to Terra. Block the node
and return the decision to the studio.

## Schedule safe waves

A node is ready only when:

1. Every dependency is accepted, not merely reported complete.
2. Its interfaces are settled at the required boundary.
3. Its owned files do not overlap another active node.
4. It does not mutate a shared schema, migration chain, lockfile, generated registry,
   design token source, or other serialization point concurrently.

Run ready, non-overlapping nodes concurrently when that reduces elapsed time. Run
shared-file edits and dependency chains serially. The primary session owns the graph,
inspects every diff, reruns every verification command, and updates node state.

Worker completion reports are claims. A node becomes `verified` only after primary
verification and `accepted` only after its required review and ledger gate succeed.

## Design authority

The studio owns visual and interaction design. Models implement and verify the accepted
design; they do not invent, improve, simplify, or reinterpret it without explicit
authorization.

Every material frontend node must identify its approved design source: Figma frame,
screenshot, prototype, design-system component, token set, motion specification, or
written state matrix. The source must define enough of the relevant layout, states,
responsive behavior, content, and motion to implement the node.

If the sources conflict or leave a material visual decision open, stop the node and ask
the studio. Do not use Terra as a substitute design authority. Any intentional visual
deviation must be listed and approved before implementation continues.

## Frontend profile

Frontend nodes must define the target routes, components, states, and viewport range.
Verification should include, where relevant:

- Type checking, linting, unit/component tests, and production build.
- Real-browser interaction for primary flows and error/empty/loading states.
- Desktop and mobile viewport evidence.
- Browser console and failed-network-request inspection.
- Keyboard navigation, visible focus, labels, and basic accessibility checks.
- Screenshot or visual evidence against the studio-approved reference.

If browser execution is unavailable, report visual QA as missing. A build passing is not
evidence that layout, interaction, responsiveness, or accessibility is correct.

Use Luna Max first for bounded frontend implementation against exact studio references,
including routes, components, states, responsive behavior, accessibility, tests, and
browser verification. Use Terra when the node requires unusually broad state
coordination, novel rendering or animation architecture, deep performance debugging,
or integration context that cannot be bounded reliably. Neither lane may make
unresolved design decisions.

## Backend profile

Backend nodes must identify the public contract, persistence effects, trust boundary,
and rollback behavior. Verification should include, where relevant:

- Unit and integration tests at the real API or service boundary.
- Request/response schema and backward-compatibility checks.
- Authentication, authorization, tenant isolation, validation, and error behavior.
- Transaction, idempotency, concurrency, retry, and duplicate-delivery behavior.
- Migration forward-path plus rollback or documented restore strategy.
- Observability without leaking secrets or customer data.

Use Luna Max first for bounded backend implementation whose contracts, invariants, and
failure behavior are explicit, including endpoints, business rules, persistence,
tests, and routine migrations with an approved strategy. Use Terra when correctness
depends on unusually subtle security, concurrency, distributed effects, migration
design, production debugging, or broad system context.

## Full-stack profile

Do not let frontend and backend workers independently invent the same interface. Create
or nominate a contract node first. It owns the shared schema, API shape, event, or types
and must be accepted before dependent implementation starts, unless the interface is
already stable and versioned. Treat the studio-approved design source as a separate
immutable frontend contract; technical interface ownership does not confer design
authority.

Once the contract is settled, Luna frontend and backend nodes may run in parallel when
their file ownership does not overlap. The integration node may also use Luna when it
is bounded by the accepted contract and complete end-to-end verification; otherwise
route it to Terra. Always exercise the real boundary, including at least one success
path and the material failure paths.

## Review and ledger boundaries

Use one execution ledger for an accumulated graph when the graph will ship as one
reviewed deliverable. Use separate ledgers when nodes are independent PRs with separate
acceptance. In either case:

- Record every worker and primary verification.
- Obtain a fresh Sol review for each independently accepted PR.
- After all nodes are integrated, rerun the complete verification suite.
- Obtain a final integration review when cross-node behavior or a stacked chain can
  fail despite individual PR approval.

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

Keep Luna-first routing where it preserves the required quality. Tighten the node
boundary or route that class to Terra when the evidence shows repeated corrections,
regressions, or failed reviews.
