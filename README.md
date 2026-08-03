# FLOC*Loom

**Sol runs the show, Luna Max builds well-specified frontend/backend nodes, Terra Max
handles capability and high-risk escalations, and a fresh Sol review with observed
runtime evidence stands between the diff and acceptance.**

FLOC*Loom is a Codex-native architect workflow for capability-routed software
delivery. The primary session stays focused on requirements, architecture, specs, and
verification while native Codex custom-agent threads handle implementation and review.

| Lane | Native agent type | Pinned profile | Use it for |
|---|---|---|---|
| Orchestrator | Primary session | GPT-5.6 Sol / High | Requirements, architecture, decomposition, routing, and acceptance |
| Preferred implementation | floc_loom_luna_implementer | GPT-5.6 Luna / Max | Bounded frontend, backend, and full-stack nodes with settled contracts |
| Escalated implementation | floc_loom_terra_implementer | GPT-5.6 Terra / Max | Broad-context or unusually high-risk technical work |
| Final review | floc_loom_sol_reviewer | GPT-5.6 Sol / High / requests read-only | Fresh review of the actual diff and verification evidence |

The final review is context-independent, not model-family-independent: Sol reviews
Sol's orchestration with a fresh context. That catches conversational assumptions, but
it is not cross-vendor review.

## Install from GitHub

Requirements:

- A current Codex CLI or ChatGPT desktop app with plugins, native subagents, and
  custom agents enabled.
- Access to GPT-5.6 Sol, Terra, and Luna at the required reasoning levels.
- Python 3.11+, Git, jq, and `shasum` for the verifier and execution ledger.

### Guided setup (recommended)

Download the setup script from the fixed `v0.4.0` release, inspect it, and run it:

~~~sh
curl -fL \
  https://raw.githubusercontent.com/GsusFC/FLOC-Loom/v0.4.0/plugins/floc-loom/scripts/setup.sh \
  -o floc-loom-setup.sh
sh floc-loom-setup.sh
~~~

One script checks the local requirements, adds the release-pinned marketplace,
installs the plugin, installs the three custom-agent profiles, verifies their exact
contents, and prints the required next step. It never overwrites a differing local
agent file.

The download deliberately uses a fixed release instead of mutable `main`, and it is
not piped directly into a shell. For a security-sensitive installation, resolve the
tag to its commit and pin that immutable commit after verification.

Start a **new Codex task** after setup passes. Native agent types are discovered at
task creation, so an existing task may not see the installed roles. Select GPT-5.6 Sol
with High reasoning for the primary session and ask for implementation work normally,
or invoke the orchestration skill explicitly:

~~~text
Use $floc-loom:orchestration to build this feature, verify it, and obtain the final Sol review before reporting done.
~~~

### Manual fallback

Plugin installation does **not** automatically install custom-agent files. That is
intentional: the files are user-owned role pins, and the installer must never overwrite
a different local role silently. If guided setup cannot be used, install both layers
manually:

~~~sh
codex plugin marketplace add GsusFC/FLOC-Loom --ref v0.4.0
codex plugin add floc-loom@floc-studio
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "floc-loom@floc-studio") | .source.path')"
test -n "$plugin_dir"
test -d "$plugin_dir"
sh "$plugin_dir/scripts/install-agents.sh"
sh "$plugin_dir/scripts/install-agents.sh" --check
~~~

Without an explicit target, the installer uses the existing CODEX_HOME value when one is
already set, otherwise the user's default Codex agents directory. It does not invoke
Codex, edit config.toml, or overwrite a differing agent file. It only installs a
missing template and then verifies every installed copy byte-for-byte.

For a larger frontend/backend build, ask FLOC*Loom for an adaptive execution graph:

~~~text
Use $floc-loom:orchestration. Build a dependency graph of task, commit, or PR-sized
deliverables. Settle shared contracts before parallel frontend/backend work, route each
node to Luna or Terra by capability, verify every node, and run a final integration
review before acceptance.
~~~

## Adaptive execution graphs

FLOC*Loom uses a direct five-part specification for one bounded change. For multiple
deliverables, parallel work, stacked PRs, or frontend/backend builds, it first creates a
delivery DAG. A graph node records its outcome, domain, dependencies, owned files,
interfaces, risk, lane, verification, integration consumers, and task/commit/PR
boundary.

Only accepted dependencies unlock a node. Nodes with overlapping files or shared
mutable contracts run serially. Independent nodes may run concurrently. A contract
node settles API schemas, events, shared types, or other interfaces before dependent
frontend and backend nodes start, followed by a real integration node.

The graph does not create branches, commits, or PRs without user authorization. PRs
are used only when a node needs its own review, rollout, revert, or merge boundary;
smaller nodes can remain tasks or commits.

Domain gates make acceptance concrete:

- **Frontend:** build and type evidence plus real-browser flows, desktop/mobile,
  console/network inspection, keyboard/focus/accessibility, and visual evidence against
  the studio-approved reference.
- **Backend:** real service-boundary tests, contract compatibility, auth and tenant
  isolation, validation, transactions/idempotency, migrations, rollback, and safe
  observability.
- **Full-stack:** an accepted shared contract, independently owned implementation
  nodes, and an integration node covering success and material failure paths.

The studio remains the design authority. Frontend nodes must name an approved Figma
frame, screenshot, prototype, design-system component, token set, motion specification,
or written state matrix. Luna and Terra implement and verify that source; neither may
invent, improve, simplify, or reinterpret it. Missing or conflicting design decisions
block the node and return to the studio.

Luna Max is the first implementation choice when a frontend or backend node is bounded,
its design and interfaces are settled, and verification can detect material failures.
Terra Max is the escalation lane for unusually broad context, subtle security,
concurrency, migration design, distributed effects, difficult debugging, or wide
integration. Routing quality should be evaluated from first-pass verification,
corrections, reviewer verdicts, scope failures, elapsed time, and usage—not anecdotes.

## Check and update

If the downloaded setup script is still available, the complete non-mutating check is:

~~~sh
sh floc-loom-setup.sh --check
~~~

The equivalent low-level check is:

~~~sh
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "floc-loom@floc-studio") | .source.path')"
test -d "$plugin_dir"
sh "$plugin_dir/scripts/install-agents.sh" --check
~~~

To update the marketplace plugin and then re-check its companion roles:

~~~sh
codex plugin marketplace upgrade floc-studio
codex plugin add floc-loom@floc-studio
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "floc-loom@floc-studio") | .source.path')"
test -d "$plugin_dir"
sh "$plugin_dir/scripts/install-agents.sh" --check
~~~

If the new shipped template differs from an installed role, the check and installer
fail rather than overwriting it. Inspect and deliberately reconcile the reported
destination with the shipped template, then rerun the check. Do not use a substitute
agent as a shortcut. Start a fresh task after every successful install or update.

## Runtime routing evidence

Native spawn/details metadata is the primary source of routing evidence. It must show
the selected custom agent type. When it also exposes model and effort, the orchestrator
compares those values with the role pin. If Desktop omits model or effort and the local
rollout is accessible, use the companion inspector as the authoritative read-only
fallback for those omitted fields:

~~~sh
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "floc-loom@floc-studio") | .source.path')"
thread_id="<native-subagent-thread-id>"
sh "$plugin_dir/scripts/inspect-agent-runtime.sh" \
  --expected-role <expected-role> \
  --expected-model <expected-model> \
  --expected-effort <expected-effort> \
  "$thread_id"
~~~

For a disposable fixture or a non-default local session root, pass it explicitly:

~~~sh
sh "$plugin_dir/scripts/inspect-agent-runtime.sh" \
  --sessions-dir /absolute/path/to/sessions \
  --expected-role <expected-role> \
  --expected-model <expected-model> \
  --expected-effort <expected-effort> \
  "$thread_id"
~~~

The helper searches only rollout filenames ending in that exact thread id, then emits a
single compact JSON object with allowlisted routing fields. It never prints prompts,
messages, environment variables, tokens, configuration contents, or arbitrary rollout
payloads. Expected role/model/effort flags make it fail on a pin mismatch. For the Sol
reviewer, also pass `--require-sandbox-type read-only --require-permission-profile`; a
missing sandbox or permission field is not evidence of isolation. If public and local
evidence both exist, they must agree.

## Execution ledger and acceptance gate

The skill is a workflow instruction, not a host-level completion hook. The companion
ledger turns its acceptance requirements into a machine-checked artifact. It records
the observed worker pins, verification commands, immutable evidence hashes, review
metadata, before/after repository snapshots, and allowed file scope.

Ledger files live outside the repository by default under `$FLOC_LOOM_RUNS_DIR`,
`$CODEX_HOME/floc-loom/runs`, or `$HOME/.codex/floc-loom/runs`. Use an explicit
`--ledger-root` for disposable runs:

~~~sh
skill_dir="/absolute/path/to/floc-loom/plugins/floc-loom/skills/orchestration"
ledger="$skill_dir/../../scripts/ledger.py"
run_id="<lowercase-uuid>"
repo="/absolute/path/to/repository"
runs_root="/absolute/path/to/runs"

python3 "$ledger" init \
  --repo "$repo" \
  --ledger-root "$runs_root" \
  --run-id "$run_id" \
  --owned-file src/example.py \
  --owned-file tests/test_example.py
run_dir="$runs_root/$run_id"
~~~

After each worker's native spawn/details evidence is accepted, record it. Record every
verification command with its actual exit code and captured output:

~~~sh
python3 "$ledger" record-worker \
  --ledger "$run_dir" \
  --thread-id <thread-id> \
  --role <observed-role> \
  --model <observed-model> \
  --effort <observed-effort> \
  --cwd "$repo"

python3 "$ledger" record-verification \
  --ledger "$run_dir" \
  --command '<exact-command>' \
  --exit-code <actual-exit-code> \
  --evidence-file /absolute/path/to/captured-output.txt
~~~

Capture the reviewer state around a fresh review, record exactly one verdict, then run
the gate:

~~~sh
python3 "$ledger" snapshot --ledger "$run_dir" --label before-review
# Spawn floc_loom_sol_reviewer with the final-review packet.
python3 "$ledger" snapshot --ledger "$run_dir" --label after-review
python3 "$ledger" record-review \
  --ledger "$run_dir" \
  --thread-id <review-thread-id> \
  --role floc_loom_sol_reviewer \
  --model gpt-5.6-sol \
  --effort high \
  --cwd "$repo" \
  --sandbox-policy-type <observed-sandbox-policy> \
  --permission-profile-type <observed-permission-profile> \
  --verdict <ship|fix-first|rethink> \
  --reason '<evidence-based reason>' \
  --residual-risk '<none or explicit residual risk>'
python3 "$ledger" accept --ledger "$run_dir"
~~~

`accept` fails when the worker pin is wrong, evidence is missing or changed, any
verification failed, the verdict is not `ship`, repository state changed during review,
or out-of-scope files changed. Hard `read-only` isolation is required by default. Use
`--allow-behavioral-read-only` only when hard isolation is not required and the broader
sandbox is reported as residual risk; never describe that mode as OS-enforced isolation.

## How routing works

The Sol orchestrator writes a five-part spec for every implementation: objective, file
ownership, interfaces, constraints, and verification. Luna Max is the preferred
implementer for bounded frontend/backend nodes, including coherent feature work. Terra
Max is selected when the node needs unusually broad context or high-risk technical
judgment. A failed Luna attempt is inspected: Sol either corrects a genuine spec gap
for one fresh attempt or escalates immediately when the evidence shows a capability or
context mismatch.

For an adaptive graph, the five-part spec also carries graph and domain routing headers.
Frontend, backend, and full-stack nodes receive their domain-specific verification
gate. Independently accepted PR nodes receive fresh reviews, and stacked or
cross-domain graphs receive a final integration review when combined behavior can fail
despite individual approval.

Before delegation and acceptance, the skill requires all of the following:

1. The installed role files pass the byte-for-byte companion check.
2. The native spawn tool exposes all three exact names in the table above.
3. Public native spawn/details metadata identifies the selected role and, when exposed,
   its expected model and effort. If model or effort is omitted, the exact-rollout local
   inspector above must provide them instead.
4. The reviewer’s observed sandbox policy type and permission profile type are captured
   and reported.

A missing, stale, conflicting, unavailable, inconsistent, or unobservable
role/model/effort stops the affected lane with an actionable error. There is no silent
model, reasoning, or agent-type fallback, and per-spawn calls do not override the role
pins.

The Sol reviewer TOML requests read-only sandboxing, but the host permission profile
may broaden that request. If the observed sandbox policy type is read-only, review can
proceed with enforced isolation. If the host broadens it, review can proceed only as
behaviorally read-only when hard isolation is not required, the prompt forbids edits,
and the parent captures and verifies exact before-and-after repository/artifact state;
the broader sandbox and permission profile must be reported as residual risk. If hard
isolation is required, the sandbox cannot be observed, or any mutation occurs, stop the
review lane and do not claim enforced read-only isolation.

The orchestrator inspects every diff and reruns verification. A fresh Sol reviewer then
returns ship, fix-first, or rethink. The session cannot report completion until the
reviewer returns ship and the execution ledger's `accept` gate succeeds. These remain
native Codex subagent threads; FLOC*Loom does not launch a nested Codex CLI process or
globally reroute unrelated subagents.

## Local development

Install a checkout and its companion agents together in a disposable or real
`CODEX_HOME`:

~~~sh
cd /absolute/path/to/floc-loom
sh plugins/floc-loom/scripts/setup.sh --local .
~~~

This is idempotent when the marketplace, plugin, and agents are already current. Use
`--target-dir <path>` for an explicit agents directory or `--check` for a non-mutating
installed-state check.

Run the repository verifier separately. It uses only a disposable target directory and
never changes your Codex configuration:

~~~sh
cd /absolute/path/to/floc-loom
sh plugins/floc-loom/scripts/verify.sh
python3 plugins/floc-loom/scripts/test_ledger.py
git diff --check
~~~

To exercise the installer itself against an explicit disposable target:

~~~sh
cd /absolute/path/to/floc-loom
scratch_agents="$(mktemp -d)"
sh plugins/floc-loom/scripts/install-agents.sh --target-dir "$scratch_agents"
sh plugins/floc-loom/scripts/install-agents.sh --target-dir "$scratch_agents" --check
~~~

To exercise only the low-level companion installer, use:

~~~sh
cd /absolute/path/to/floc-loom
sh plugins/floc-loom/scripts/install-agents.sh
sh plugins/floc-loom/scripts/install-agents.sh --check
~~~

After editing the plugin, validate both layers:

~~~sh
cd /absolute/path/to/floc-loom
if [ -n "$CODEX_HOME" ]; then
  codex_skills="$CODEX_HOME/skills/.system"
else
  codex_skills="$HOME/.codex/skills/.system"
fi
uv run --no-project --with pyyaml python "$codex_skills/skill-creator/scripts/quick_validate.py" plugins/floc-loom/skills/orchestration
uv run --no-project --with pyyaml python "$codex_skills/plugin-creator/scripts/validate_plugin.py" plugins/floc-loom
jq empty .agents/plugins/marketplace.json plugins/floc-loom/.codex-plugin/plugin.json
~~~

The verifier validates JSON and TOML, role pins, installer clean/idempotent/check and
conflict behavior, runtime-inspector safe fixtures, ledger acceptance and rejection
cases, contract references, and shell syntax. The uv commands supply the validators'
PyYAML dependency in a disposable environment. They do not install the marketplace or
mutate Codex configuration.

## Origin and license

FLOC*Loom is derived from [DannyMac180/sol-advisor](https://github.com/DannyMac180/sol-advisor),
which was released under the MIT License. The upstream copyright notice and repository
history are preserved. This version is maintained independently by FLOC* and is not an
official release of the original project.

MIT
