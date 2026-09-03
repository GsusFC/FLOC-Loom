# FLOC*Loom

**Sol owns architecture and acceptance; Luna Max implements bounded work; Terra Max
handles broad-context or high-risk implementation; a route-aware ledger prevents weak
evidence from being accepted as a strong delivery.**

FLOC*Loom is a Codex-native software-delivery workflow. The primary Sol/High session
keeps requirements, architecture, routing, and verification under human-led control
while native custom-agent threads implement or review only under role-pinned contracts.

| Responsibility | Native agent type | Pinned profile | Use it for |
|---|---|---|---|
| Orchestrator | Primary session | GPT-5.6 Sol / High | Requirements, architecture, route selection, verification, acceptance |
| Bounded implementation | `floc_loom_luna_implementer` | GPT-5.6 Luna / Max | Settled, bounded frontend/backend/full-stack work |
| High-risk implementation | `floc_loom_terra_implementer` | GPT-5.6 Terra / Max | Broad context, migrations, security, concurrency, distributed effects, integration |
| Fresh review | `floc_loom_sol_reviewer` | GPT-5.6 Sol / High / requests read-only | Independent-context review of the actual diff and evidence |

The final review is context-independent, not model-family-independent: Sol reviews the
orchestration with a fresh context. It catches conversational assumptions; it is not
cross-vendor review.

## Install from GitHub

Requirements:

- A current Codex CLI or ChatGPT desktop app with plugins, native subagents, and custom
  agents enabled.
- Access to GPT-5.6 Sol, Terra, and Luna at the required reasoning levels.
- Python 3.11+, Git, jq, and `shasum` or `sha256sum` for verification and the ledger.

### Guided setup (recommended)

Download the setup script from the fixed `v0.5.0` release, inspect it, and run it:

~~~sh
curl -fL \
  https://raw.githubusercontent.com/GsusFC/FLOC-Loom/v0.5.0/plugins/floc-loom/scripts/setup.sh \
  -o floc-loom-setup.sh
sh floc-loom-setup.sh
~~~

The script checks local requirements, adds the release-pinned marketplace, installs the
plugin, installs or safely migrates the three custom-agent profiles, verifies exact
contents, and prints the required next step. It never overwrites an arbitrary differing
local role file. The download uses a fixed release instead of mutable `main` and is not
piped directly into a shell.

Start a **new Codex task** after setup passes: native agent types are discovered at task
creation. Select GPT-5.6 Sol with High reasoning, then use the skill:

~~~text
Use $floc-loom:orchestration to build this feature, verify it, and accept it through the appropriate route.
~~~

### Manual fallback

Plugin installation does not automatically install custom-agent files because those
files are user-owned role pins. If the direct download cannot be used, make a local
checkout of the same fixed release and run that checkout's canonical setup script:

~~~sh
git clone --branch v0.5.0 --depth 1 https://github.com/GsusFC/FLOC-Loom.git floc-loom-v0.5.0
setup="floc-loom-v0.5.0/plugins/floc-loom/scripts/setup.sh"
sh "$setup" --local "$PWD/floc-loom-v0.5.0"
sh "$setup" --check
~~~

The setup script proves the installed manifest is exactly `floc-loom` version `0.5.0`
before it executes the installed companion-agent helper. A role-scoped check is only a
post-currentness diagnostic; it cannot establish that the marketplace plugin is current.

## The user journey and tradeoffs

1. **Read-only discovery and role preflight.** Confirm the primary Sol/High session,
   exact installed roles, and actual native routing metadata.
2. **Apply the minimal-change gate.** Identify the observed failure or invariant,
   inspect the closest existing mechanism, and state what must remain unchanged.
3. **Declare one route per direct deliverable or graph node** before its first mutation
   or auxiliary spawn. A route can only escalate.
4. **Implement and verify.** The primary session inspects the real diff and reruns the
   required checks; worker reports are evidence claims, not acceptance.
5. **Accept through the route gate.** The ledger records immutable route/evidence state
   for every non-solo route. `solo` remains a tightly bounded primary-only exception.

Reusing an existing mechanism means using its current path and semantics. It does not
authorize a wrapper, new version, parallel adapter/service, schema, lock, index,
migration, or durable state. Architectural expansion needs concrete evidence and
explicit approval in the task or spec; adjacent future-proofing remains a non-goal.

| Route | Tradeoff | Required acceptance |
|---|---|---|
| `solo` | Lowest ceremony, only for read-only work or one-file mechanical low-risk change | No auxiliary or ledger; reclassify before boundary expansion |
| `delegate` | Faster bounded Luna implementation without final review | One Luna worker, primary verification, unchanged verified-state binding |
| `audit` | Primary implementation retains control while a fresh Sol checks it | Primary verification plus fresh Sol review; worker evidence is rejected |
| `full` | Strongest worker + reviewer path for consequential or high-risk work | One Luna/Terra worker, primary verification, fresh Sol review |

Independently accepted PRs and consequential integration use `audit` or `full`. Work
that reaches the review-trigger surfaces defined in the role contracts also uses
`audit` or `full`; if an implementer is used, it uses `full`. This prevents privacy or
observability-sensitive changes from bypassing final review through a reviewer-free
route.

Every final review emits non-sensitive `COVERAGE` evidence. When the conditional sweep
does not trigger, it records no triggers or inspected categories and justifies every
category exclusion. It never records payloads, complete URLs, credentials, bodies,
prompts, tokens, environment values, or configuration values. A
review boundary gets one bundled `fix-first` correction; a new blocker in the fresh
post-bundle review is `rethink`, not a loop-until-clean patch cycle. The ledger stores
only the final `ship` review as acceptance evidence. A non-ship verdict is handled
before persistence, then a corrected and reverified diff starts a fresh review boundary.
The installed ledger's `coverage-schema --json` command is the public exact mapping for
coverage IDs and artifact fields; do not copy identifiers from implementation source.

## Adaptive execution graphs

Use a direct five-part specification for one bounded change. For multiple deliverables,
parallel work, stacked PRs, or frontend/backend work, ask FLOC*Loom to create a delivery
DAG:

~~~text
Use $floc-loom:orchestration. Build a dependency graph of task, commit, or PR-sized
deliverables. Declare a route per node, settle shared contracts before parallel
frontend/backend work, apply domain verification, and accept each node through its
route-aware evidence gate.
~~~

A graph node names outcome, domain, dependencies, exact owned files, interfaces,
design source, risk, route, lane, verification, and integration checks. Nodes with
overlapping files or shared mutable contracts run serially. Independent nodes may run
concurrently. A contract node settles shared schemas/events/types before dependent
frontend/backend nodes start; cross-boundary behavior gets an integration node.

The studio remains the visual-design authority. A frontend node must identify an
approved design source (Figma frame, screenshot, prototype, component, token set,
motion specification, or state matrix). Neither Luna nor Terra may invent or
reinterpret missing design decisions.

## Runtime routing and acceptance

Public native spawn/details metadata is the primary routing evidence. If model or
effort is absent there, use the plugin's exact-rollout read-only inspector. The reviewer
also reports its observed sandbox policy and permission profile. A requested read-only
TOML is not proof of host-enforced isolation.

The execution ledger lives outside the repository by default under
`$FLOC_LOOM_RUNS_DIR`, `$CODEX_HOME/floc-loom/runs`, or
`$HOME/.codex/floc-loom/runs`. It persists the non-solo route at initialization,
records monotonic escalation, role pins, immutable verification hashes, repository
state, review evidence, and allowed-file scope. It fails closed on missing/wrong
route evidence, changed verification state, changed review state, out-of-scope files,
or an incomplete route matrix.

The orchestration skill's mandatory [operations reference](plugins/floc-loom/skills/orchestration/references/operations.md)
contains exact ledger, runtime-observation, coverage-artifact, installer-maintenance,
and test commands. Do not copy a command from memory: resolve helpers from the installed
skill directory so the shipped version supplies the behavior being run.

## Check and update

If the downloaded setup script is still available:

~~~sh
sh floc-loom-setup.sh --check
~~~

The v0.5 setup check refuses an older installed plugin before it invokes that plugin's
companion-agent installer. A role-only check is not a plugin-currentness check.

If the check reports a missing marketplace or plugin, re-enter the canonical setup
path and then re-check it:

~~~sh
sh floc-loom-setup.sh
sh floc-loom-setup.sh --check
~~~

### Ref-pinned v0.4 recovery

Do **not** use `codex plugin marketplace upgrade` to move a v0.4 marketplace to v0.5:
it refreshes the configured source but does not change its pinned ref. The following is
a deliberate transition. It removes only the configured `floc-studio` marketplace
source; it does not delete companion-agent role files.

~~~sh
codex plugin marketplace remove floc-studio
codex plugin marketplace add GsusFC/FLOC-Loom --ref v0.5.0
codex plugin add floc-loom@floc-studio --json
sh floc-loom-setup.sh
sh floc-loom-setup.sh --check
~~~

Use that transition only after the v0.5 setup refusal identifies a version-mismatched
or ref-pinned stale plugin. If the downloaded script is unavailable, repeat the
fixed-release download in [Guided setup](#guided-setup-recommended) first. Do not use
an installed `install-agents.sh` invocation as an equivalent currentness check. When a
current v0.5 check finds a historical Sol reviewer, rerun `sh floc-loom-setup.sh` to
perform the allowlisted migration; reconcile any other role difference deliberately.
Start a fresh task after a successful role update.

## Local development

Install a checkout and its companion agents in a disposable or real `CODEX_HOME`:

~~~sh
cd /absolute/path/to/floc-loom
sh plugins/floc-loom/scripts/setup.sh --local .
~~~

Validate behavior before shipping a plugin change:

~~~sh
cd /absolute/path/to/floc-loom
python3 -m unittest plugins/floc-loom/scripts/test_ledger.py
sh plugins/floc-loom/scripts/test_install_agents.sh
sh plugins/floc-loom/scripts/verify.sh
git diff --check
~~~

For plugin-schema validation, if the local Codex skills are present:

~~~sh
if [ -n "$CODEX_HOME" ]; then
  codex_skills="$CODEX_HOME/skills/.system"
else
  codex_skills="$HOME/.codex/skills/.system"
fi
uv run --no-project --with pyyaml python "$codex_skills/skill-creator/scripts/quick_validate.py" plugins/floc-loom/skills/orchestration
uv run --no-project --with pyyaml python "$codex_skills/plugin-creator/scripts/validate_plugin.py" plugins/floc-loom
jq empty .agents/plugins/marketplace.json plugins/floc-loom/.codex-plugin/plugin.json
~~~

## Origin and license

FLOC*Loom is derived from [DannyMac180/sol-advisor](https://github.com/DannyMac180/sol-advisor),
released under the MIT License. The upstream copyright notice and repository history are
preserved. This version is maintained independently by FLOC* and is not an official
release of the original project.

MIT
