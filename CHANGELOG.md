# Changelog

## 0.5.0

- Added selective `solo`, `delegate`, `audit`, and `full` routes with monotonic
  escalation and route-aware acceptance evidence.
- Added a minimal-change architecture gate that requires inspection of the closest
  existing mechanism and forbids semantic expansion without evidence and approval.
- Bound final review to the completed worker/verification matrix and exact review
  snapshot before persisting acceptance evidence.
- Made one bundled `fix-first` correction operational without adding a correction-count
  state machine; only the final `ship` review is persisted.
- Allowed diagnostic failed-verification history while still requiring a successful
  verification bound to the terminal repository state.
- Replaced persisted raw verification commands with short non-sensitive labels.
- Added conditional non-sensitive security/observability coverage, safer role migration,
  portable setup recovery, and Linux/macOS verification.

## 0.4.0

- Renamed the independently maintained workflow to FLOC*Loom, with the technical
  plugin ID `floc-loom` and the `floc-studio` marketplace.
- Added a release-pinned unified setup script that installs the marketplace plugin and
  companion agents, verifies them, supports local checkouts and provides a read-only
  `--check` mode without weakening conflict protection.
- Added adaptive execution graphs for multi-deliverable, parallel, stacked-PR, and
  frontend/backend work.
- Made Luna Max the preferred implementation lane for bounded, well-specified
  frontend/backend nodes, including coherent feature work; Terra Max handles
  capability and unusually high-risk escalation.
- Added frontend, backend, and full-stack verification profiles plus contract-first
  integration rules.
- Made studio-approved design sources immutable implementation contracts; missing
  visual decisions now block a node instead of being delegated to a model.
- Added per-PR and final integration review boundaries for graph-shaped delivery.
- Added evidence-based routing evaluation guidance so Luna/Terra decisions can be
  refined from observed outcomes instead of anecdotes.

## 0.3.0

- Added a fail-closed execution ledger with worker, verification, review, snapshot,
  scope, and acceptance evidence.
- Added strict expected role/model/effort and reviewer sandbox checks to the runtime
  inspector.
- Hardened installer argument handling, target canonicalization, and root protection.
- Added disposable ledger regression tests and GitHub Actions validation.
- Documented immutable release pinning and residual risk for behavioral read-only review.

## 0.2.0

- Initial Codex-native workflow with Luna, Terra, and Sol custom-agent roles, before
  the FLOC*Loom rename.
