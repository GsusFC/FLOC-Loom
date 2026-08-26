#!/bin/sh
# Repository-local verification for FLOC*Loom v0.5 route, ledger, and installer contracts.

set -eu

pass() {
  printf '%s\n' "PASS: $*"
}

fail() {
  printf '%s\n' "FAIL: $*" >&2
  exit 1
}

script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd) || exit 1
plugin_dir=$(CDPATH='' cd "$script_dir/.." && pwd) || exit 1
repo_root=$(CDPATH='' cd "$plugin_dir/../.." && pwd) || exit 1
readme=$repo_root/README.md
installer=$script_dir/install-agents.sh
installer_tests=$script_dir/test_install_agents.sh
setup=$script_dir/setup.sh
runtime_inspector=$script_dir/inspect-agent-runtime.sh
ledger=$script_dir/ledger.py
ledger_tests=$script_dir/test_ledger.py
templates=$plugin_dir/agents
manifest=$plugin_dir/.codex-plugin/plugin.json
skill=$plugin_dir/skills/orchestration/SKILL.md
contracts=$plugin_dir/skills/orchestration/references/role-contracts.md
operations=$plugin_dir/skills/orchestration/references/operations.md
execution_graphs=$plugin_dir/skills/orchestration/references/execution-graphs.md

for required in "$readme" "$installer" "$installer_tests" "$setup" "$runtime_inspector" "$ledger" "$ledger_tests" "$manifest" "$skill" "$contracts" "$operations" "$execution_graphs"; do
  test -f "$required" || fail "required shipped file is missing: $required"
done

jq empty "$manifest"
jq -e '.version == "0.5.0"' "$manifest" >/dev/null || fail "plugin manifest version is not 0.5.0"
pass "plugin manifest JSON and v0.5.0 release version"

python3 - "$templates" "$skill" "$contracts" "$operations" "$execution_graphs" "$manifest" "$ledger" "$readme" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError as exc:
    raise SystemExit("Python 3.11+ with tomllib is required for TOML validation") from exc

templates, skill, contracts, operations, graphs, manifest, ledger, readme = map(Path, sys.argv[1:])
expected = {
    "floc-loom-luna-implementer.toml": {
        "name": "floc_loom_luna_implementer",
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "max",
    },
    "floc-loom-terra-implementer.toml": {
        "name": "floc_loom_terra_implementer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "max",
    },
    "floc-loom-sol-reviewer.toml": {
        "name": "floc_loom_sol_reviewer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
}
for filename, pins in expected.items():
    path = templates / filename
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for field in ("name", "description", "developer_instructions"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"{path}: missing or empty required {field!r}")
    for field, expected_value in pins.items():
        if data.get(field) != expected_value:
            raise SystemExit(f"{path}: {field}={data.get(field)!r}, expected {expected_value!r}")

reviewer = tomllib.loads((templates / "floc-loom-sol-reviewer.toml").read_text(encoding="utf-8"))["developer_instructions"]
for fragment in (
    "COVERAGE",
    "non-sensitive",
    "fix-first",
    "post-bundle",
    "rethink",
    "Remain strictly read-only",
):
    if fragment not in reviewer:
        raise SystemExit(f"reviewer TOML lacks semantic mirror: {fragment!r}")
if "provider/client I/O" in reviewer or "Application logs, failure records" in reviewer:
    raise SystemExit("reviewer TOML duplicates the role-contract sweep taxonomy")

contents = {"skill": skill.read_text(encoding="utf-8"), "contracts": contracts.read_text(encoding="utf-8"), "operations": operations.read_text(encoding="utf-8"), "graphs": graphs.read_text(encoding="utf-8")}


def executable_shell_fences(document: str) -> list[tuple[int, str]]:
    """Return every shell-like Markdown fence with its source line."""
    opening = re.compile(r"(?m)^[ ]{0,3}(?P<marker>`{3,}|~{3,})(?P<language>[^\n]*)\n")
    shell_languages = {"sh", "bash", "shell", "zsh", "dash", "ksh"}
    fences: list[tuple[int, str]] = []
    position = 0
    while match := opening.search(document, position):
        marker = match.group("marker")
        closing = re.compile(
            rf"(?m)^[ ]{{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$"
        ).search(document, match.end())
        if closing is None:
            raise SystemExit("README contains an unclosed Markdown fence")
        language = match.group("language").strip().split(maxsplit=1)
        if language and language[0].lower() in shell_languages:
            line = document.count("\n", 0, match.start()) + 1
            fences.append((line, document[match.end() : closing.start()]))
        position = closing.end()
    return fences


readme_text = readme.read_text(encoding="utf-8")
shell_fences = executable_shell_fences(readme_text)
if not shell_fences:
    raise SystemExit("README must contain executable setup/check shell fences")

# The public README must not contain an installed-helper path or a plugin-path resolver
# in any executable fence. Reject those shapes anywhere in a fence, rather than trying
# to model shell prefixes, functions, substitutions, or variable names.
direct_helper = re.compile(r"\binstall-agents\.sh\b", re.IGNORECASE)
plugin_list = re.compile(r"\bplugin\s+list\b.*?--json\b", re.IGNORECASE | re.DOTALL)
source_path = re.compile(
    r"""(?ix)
    (?:
        \.\s*source\s*\.\s*path\b
      | \[\s*[\"']source[\"']\s*\]\s*\[\s*[\"']path[\"']\s*\]
      | \.\s*source\s*\[\s*[\"']path[\"']\s*\]
      | \[\s*[\"']source[\"']\s*\]\s*\.\s*path\b
    )
    """
)


def unsafe_public_commands(fences: list[tuple[int, str]]) -> list[str]:
    unsafe: list[str] = []
    for line, body in fences:
        normalized = re.sub(r"\\[ \t]*\n", " ", body)
        if direct_helper.search(normalized):
            unsafe.append(f"line {line}: direct installed helper invocation")
        if plugin_list.search(normalized) and source_path.search(normalized):
            unsafe.append(f"line {line}: installed plugin-path resolution")
    return unsafe


unsafe_fences = unsafe_public_commands(shell_fences)
if unsafe_fences:
    raise SystemExit("README public command surface bypasses the setup manifest gate: " + "; ".join(unsafe_fences))

# Prove the ratchet handles indented fences and adversarial wrappers rather than only
# matching a historic command position or variable name.
probes = {
    "subshell function resolver": """   ~~~bash
resolve_current() {
  installed_root="$(codex plugin list --json | jq -r '.installed[] | .source.path')"
}
   ~~~
""",
    "renamed multiline resolver": """~~~sh
tool=codex
installed_root="$(
  "$tool" plugin \\
    list \\
    --json | jq -r '.installed[] | .source["path"]'
)"
~~~
""",
    "wrapped helper": """~~~zsh
launch() { exec sh "$candidate/scripts/install-agents.sh" --check; }
! sudo timeout 5 sh "$candidate/scripts/install-agents.sh" --check
~~~
""",
}
for label, probe in probes.items():
    if not unsafe_public_commands(executable_shell_fences(probe)):
        raise SystemExit(f"README command-surface ratchet does not recognize {label}")

canonical_check = re.compile(r"(?m)^\s*(?:sh|bash|dash|ksh|zsh)\s+[^\s;|&]*setup[^\s;|&]*\s+--check\b")
if not any(canonical_check.search(body) for _, body in shell_fences):
    raise SystemExit("README must retain an executable canonical setup --check recovery path")
if "https://raw.githubusercontent.com/GsusFC/FLOC-Loom/v0.5.0/plugins/floc-loom/scripts/setup.sh" not in readme_text:
    raise SystemExit("README must retain the fixed v0.5.0 setup download")
for recovery_fragment in (
    "codex plugin marketplace remove floc-studio",
    "codex plugin marketplace add GsusFC/FLOC-Loom --ref v0.5.0",
    "codex plugin add floc-loom@floc-studio --json",
    "does not change its pinned ref",
    "does not delete companion-agent role files",
):
    if recovery_fragment not in readme_text:
        raise SystemExit(f"README lacks the executable v0.4 ref-transition recovery: {recovery_fragment!r}")

required = {
    "skill": (
        "references/role-contracts.md",
        "references/operations.md",
        "references/execution-graphs.md",
        "Declare a selective route before work",
        "solo",
        "delegate",
        "audit",
        "full",
        "before its first mutation or auxiliary\nspawn",
        "Routes may only escalate.",
        "Consequential integration boundaries and independently accepted PR boundaries require",
        "conditional review-trigger surface",
        "role-contracts.md](references/role-contracts.md#conditional-security-and-observability-sweep)",
        "agent_type: floc_loom_luna_implementer",
        "agent_type: floc_loom_terra_implementer",
        "agent_type: floc_loom_sol_reviewer",
        "fork_turns: none",
    ),
    "contracts": (
        "Conditional security and observability sweep",
        "provider/client I/O",
        "logging or telemetry",
        "exception handling",
        "schemas or serialization",
        "configuration",
        "URLs or credentials",
        "transport debugging",
        "Ingress, parsing, validation, and serialization.",
        "Success, exception, fallback, cache, and early-return control flow.",
        "Application logs, failure records, usage observations, summaries, and",
        "Configuration-derived endpoint and URL metadata.",
        "Stale state across sequential calls plus safe/default transitions.",
        "COVERAGE",
        "payloads, complete URLs, credentials, bodies, prompt content, tokens, environment",
        "One correction bundle per review boundary",
        "post-bundle review finds another blocker, it returns `rethink`",
        "proceed`,\n`change`, or `stop`",
        "delegate` | One Luna worker",
        "audit` | Successful primary verification and fresh Sol review",
        "full` | One Luna or Terra worker",
    ),
    "operations": (
        "This reference owns executable workflow mechanics",
        "--check-role luna",
        "--route <delegate|audit|full>",
        "python3 \"$ledger\" escalate",
        "--label verified-state",
        "coverage-schema --json",
        "--coverage-file",
        "no native correction-count ledger state machine",
    ),
    "graphs": (
        "ROUTE: solo | delegate | audit | full",
        "LANE: none | Luna | Terra",
        "one-auxiliary",
        "Integration nodes and independently accepted PR nodes must choose `audit` or `full`",
        "verified-state",
    ),
}
for name, fragments in required.items():
    for fragment in fragments:
        if fragment not in contents[name]:
            raise SystemExit(f"{name} lacks required semantic text: {fragment!r}")

# Operations and public docs may link to the source, but only role-contracts may carry
# the full sink/control-flow taxonomy.
full_taxonomy = "Application logs, failure records, usage observations, summaries, and"
for name in ("skill", "operations", "graphs"):
    if full_taxonomy in contents[name]:
        raise SystemExit(f"{name} duplicates the role-contract sweep taxonomy")

for document_name, document in (("skill", contents["skill"]), ("contracts", contents["contracts"])):
    if re.search(r"(?m)^\s*(model|reasoning_effort):", document):
        raise SystemExit(f"per-spawn model or reasoning override remains in {document_name}")

# The ledger is the only public exact ID mapping. Verify its deterministic document
# against the role-contract semantic source instead of relying on substring guards.
result = subprocess.run(
    [sys.executable, str(ledger), "coverage-schema", "--json"],
    check=False,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
if result.returncode != 0:
    raise SystemExit(f"coverage-schema discovery failed: {result.stderr.strip()}")
try:
    coverage_schema = json.loads(result.stdout)
except json.JSONDecodeError as exc:
    raise SystemExit(f"coverage-schema discovery emitted invalid JSON: {exc}") from exc
if not isinstance(coverage_schema, dict):
    raise SystemExit("coverage-schema discovery must emit a JSON object")

required_schema_keys = {
    "schema_version",
    "coverage_schema_version",
    "semantic_source",
    "required_fields",
    "exclusion_required_fields",
    "validation_rules",
    "triggers",
    "categories",
    "fingerprint",
}
if set(coverage_schema) != required_schema_keys:
    raise SystemExit("coverage-schema discovery keys do not match the public contract")
if coverage_schema.get("schema_version") != 1 or coverage_schema.get("coverage_schema_version") != 1:
    raise SystemExit("coverage-schema discovery version is unsupported")
if coverage_schema.get("semantic_source") != "references/role-contracts.md#conditional-security-and-observability-sweep":
    raise SystemExit("coverage-schema discovery does not identify the role-contract semantic source")
if coverage_schema.get("required_fields") != ["schema_version", "sweep_triggered", "triggers", "inspected", "exclusions"]:
    raise SystemExit("coverage-schema discovery has an unexpected coverage artifact field contract")
if coverage_schema.get("exclusion_required_fields") != ["category", "reason"]:
    raise SystemExit("coverage-schema discovery has an unexpected exclusion field contract")

coverage_core = {key: value for key, value in coverage_schema.items() if key != "fingerprint"}
computed_fingerprint = "sha256:" + hashlib.sha256(
    json.dumps(coverage_core, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if coverage_schema.get("fingerprint") != computed_fingerprint:
    raise SystemExit("coverage-schema discovery fingerprint does not bind its exact mapping")
contract_fingerprint = re.search(r"(?m)^Machine coverage schema fingerprint: `([^`]+)`$", contents["contracts"])
if contract_fingerprint is None:
    raise SystemExit("role-contracts lacks the coverage-schema fingerprint binding")
if contract_fingerprint.group(1) != computed_fingerprint:
    raise SystemExit("ledger coverage IDs or meanings drifted from the role-contract fingerprint")

for field, expected_count in (("triggers", 10), ("categories", 5)):
    entries = coverage_schema[field]
    if not isinstance(entries, list) or len(entries) != expected_count:
        raise SystemExit(f"coverage-schema {field} must expose exactly {expected_count} entries")
    identifiers = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id", "semantic_text"}:
            raise SystemExit(f"coverage-schema {field} entry has an invalid public shape")
        identifier = entry["id"]
        semantic_text = entry["semantic_text"]
        if not isinstance(identifier, str) or not identifier or not isinstance(semantic_text, str) or not semantic_text:
            raise SystemExit(f"coverage-schema {field} entry has an invalid ID or semantic text")
        if semantic_text not in contents["contracts"]:
            raise SystemExit(f"coverage-schema {field} semantic text is absent from role-contracts: {identifier}")
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise SystemExit(f"coverage-schema {field} IDs are not unique")

drifted_core = json.loads(json.dumps(coverage_core))
drifted_core["triggers"][0]["id"] = "identifier-drift"
drifted_fingerprint = "sha256:" + hashlib.sha256(
    json.dumps(drifted_core, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if drifted_fingerprint == computed_fingerprint:
    raise SystemExit("coverage-schema fingerprint does not detect identifier drift")

if '"version": "0.5.0"' not in manifest.read_text(encoding="utf-8"):
    raise SystemExit("manifest source does not contain v0.5.0")
print("README public command surfaces, shipped route, review, public coverage schema, operations-link, and TOML semantics are valid")
PY
pass "semantic shipped-copy contract checks"

# The focused fixture contains the exact v0.4 historical Sol reviewer, role-scoped
# checks, modified-file refusal, zero-mutation conflict preflight, and symlink cases.
sh "$installer_tests"
pass "installer role checks, v0.4 migration, conflict preflight, and symlink refusals"

grep -Fq 'v040_sol_reviewer_sha256=' "$installer" || fail "installer does not pin the allowlisted v0.4 Sol template"
grep -Fq 'destination became a symlink after preflight' "$installer" || fail "installer lacks immediate destination-symlink revalidation"
grep -Fq 'assert_safe_parent_chain' "$installer" || fail "installer lacks parent-symlink defense"
grep -Fq 'mv -f "$staged" "$destination"' "$installer" || fail "installer lacks atomic historical replacement"
pass "installer shipped migration and symlink defense semantics"

python3 -m unittest "$ledger_tests"
pass "route-aware ledger matrices, coverage validation, escalation, and state binding"

# Setup's fake Codex fixture guards that the shipped v0.5 setup script pins the same
# release metadata as the manifest, rejects a stale v0.4 plugin before its installer can
# run, and still runs installer preflight after a current install.
tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in
  /*) ;;
  *) tmp_base=/tmp ;;
esac
tmp_base=$(CDPATH='' cd -P "$tmp_base" && pwd -P) || fail "could not resolve verifier temporary directory"
tmp_dir=''
cleanup() {
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    case "$tmp_dir" in
      "$tmp_base"/floc-loom-verify.*) rm -rf "$tmp_dir" ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
    esac
  fi
}
trap cleanup 0 HUP INT TERM
tmp_dir=$(mktemp -d "$tmp_base/floc-loom-verify.XXXXXX") || fail "could not create verifier fixture directory"

fake_codex=$tmp_dir/fake-codex
fake_codex_log=$tmp_dir/fake-codex.log
fake_codex_state=$tmp_dir/current-marketplace.state
setup_codex_home=$tmp_dir/setup-codex-home
cat > "$fake_codex" <<'EOF'
#!/bin/sh
set -eu

: "${FAKE_CODEX_LOG:?}"
: "${FAKE_CODEX_STATE:?}"
: "${FAKE_PLUGIN_V050_DIR:?}"

printf '%s\n' "$*" >> "$FAKE_CODEX_LOG"
if [ -n "${FAKE_CODEX_ARGV_LOG:-}" ]; then
  jq -n --args '$ARGS.positional' -- "$@" >> "$FAKE_CODEX_ARGV_LOG"
fi

state_name=''
state_source=''
state_ref=''
state_plugin_installed=0

load_state() {
  if [ -f "$FAKE_CODEX_STATE" ]; then
    IFS='|' read -r state_name state_source state_ref state_plugin_installed < "$FAKE_CODEX_STATE" \
      || { printf '%s\n' "invalid fake marketplace state" >&2; exit 1; }
  fi
}

write_state() {
  printf '%s|%s|%s|%s\n' "$1" "$2" "$3" "$4" > "$FAKE_CODEX_STATE"
  state_name=$1
  state_source=$2
  state_ref=$3
  state_plugin_installed=$4
}

select_plugin() {
  case "$state_ref" in
    v0.4.0)
      selected_path=${FAKE_PLUGIN_V040_DIR:?}
      selected_version=0.4.0
      ;;
    *)
      selected_path=$FAKE_PLUGIN_V050_DIR
      selected_version=0.5.0
      ;;
  esac
}

load_state
case "${1-} ${2-} ${3-}" in
  "plugin marketplace add")
    source=${4-}
    [ -n "$source" ] || { printf '%s\n' "missing fake marketplace source" >&2; exit 1; }
    ref=local
    if [ "${5-}" = '--ref' ]; then
      ref=${6-}
    fi
    if [ -n "$state_name" ]; then
      if [ "$state_source" != "$source" ] || [ "$state_ref" != "$ref" ]; then
        printf '%s\n' "marketplace 'floc-studio' is already added from a different source; remove it before adding this source" >&2
        exit 1
      fi
      already_added=true
    else
      write_state floc-studio "$source" "$ref" 0
      already_added=false
    fi
    jq -n --arg name floc-studio --argjson already_added "$already_added" \
      '{marketplaceName:$name,installedRoot:"/fixture",alreadyAdded:$already_added}'
    ;;
  "plugin marketplace remove")
    [ "${4-}" = floc-studio ] && [ "$state_name" = floc-studio ] \
      || { printf '%s\n' "fake marketplace is not configured" >&2; exit 1; }
    rm -f "$FAKE_CODEX_STATE"
    state_name=''
    jq -n '{marketplaceName:"floc-studio",removed:true}'
    ;;
  "plugin marketplace upgrade")
    [ "${4-}" = floc-studio ] && [ "$state_name" = floc-studio ] \
      || { printf '%s\n' "fake marketplace is not configured" >&2; exit 1; }
    jq -n --arg name "$state_name" --arg ref "$state_ref" '{marketplaceName:$name,ref:$ref,upgraded:true}'
    ;;
  "plugin marketplace list")
    if [ -n "$state_name" ]; then
      jq -n --arg name "$state_name" --arg source "$state_source" --arg ref "$state_ref" \
        '{marketplaces:[{name:$name,root:"/fixture",marketplaceSource:{sourceType:"git",source:$source,ref:$ref}}]}'
    else
      jq -n '{marketplaces:[]}'
    fi
    ;;
  "plugin add "*)
    [ "${3-}" = floc-loom@floc-studio ] && [ "$state_name" = floc-studio ] \
      || { printf '%s\n' "fake plugin marketplace is unavailable" >&2; exit 1; }
    write_state "$state_name" "$state_source" "$state_ref" 1
    select_plugin
    jq -n --arg path "$selected_path" --arg version "$selected_version" \
      '{pluginId:"floc-loom@floc-studio",name:"floc-loom",marketplaceName:"floc-studio",version:$version,installedPath:$path,authPolicy:"ON_INSTALL"}'
    ;;
  "plugin list "*)
    if [ "$state_name" = floc-studio ] && [ "$state_plugin_installed" = 1 ]; then
      select_plugin
      jq -n --arg path "$selected_path" --arg version "$selected_version" \
        '{installed:[{pluginId:"floc-loom@floc-studio",name:"floc-loom",marketplaceName:"floc-studio",version:$version,installed:true,enabled:true,source:{source:"local",path:$path}}],available:[]}'
    else
      jq -n '{installed:[],available:[]}'
    fi
    ;;
  *)
    printf '%s\n' "unexpected fake Codex command: $*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$fake_codex"
FAKE_CODEX_LOG="$fake_codex_log" \
FAKE_CODEX_STATE="$fake_codex_state" \
FAKE_PLUGIN_V050_DIR="$plugin_dir" \
CODEX_BIN="$fake_codex" \
CODEX_HOME="$setup_codex_home" \
  sh "$setup" --local "$repo_root"
FAKE_CODEX_LOG="$fake_codex_log" \
FAKE_CODEX_STATE="$fake_codex_state" \
FAKE_PLUGIN_V050_DIR="$plugin_dir" \
CODEX_BIN="$fake_codex" \
CODEX_HOME="$setup_codex_home" \
  sh "$setup" --check
for agent_file in floc-loom-luna-implementer.toml floc-loom-terra-implementer.toml floc-loom-sol-reviewer.toml; do
  cmp -s "$templates/$agent_file" "$setup_codex_home/agents/$agent_file" \
    || fail "unified setup did not install the exact agent template: $agent_file"
done
grep -Fq "plugin marketplace add $repo_root --json" "$fake_codex_log" \
  || fail "unified setup did not add the selected local marketplace"
grep -Fq 'plugin add floc-loom@floc-studio --json' "$fake_codex_log" \
  || fail "unified setup did not install the marketplace plugin"
pass "unified setup and v0.5 plugin fixture"

default_source=$(sed -n 's/^default_source=//p' "$setup")
default_ref=$(sed -n 's/^default_ref=//p' "$setup")
default_version=$(sed -n 's/^default_version=//p' "$setup")
test -n "$default_source" && test -n "$default_ref" && test -n "$default_version" \
  || fail "setup defaults are unavailable to the ref-transition fixture"

# Reuse the shipped exact historical fixture and bind it to the installer's allowlisted
# hash. That keeps this stateful setup test anchored to the same v0.4 migration input.
historical_sol=$tmp_dir/v040-sol-reviewer.toml
awk '
  /^name = "floc_loom_sol_reviewer"$/ { emit = 1 }
  emit && /^EOF$/ { exit }
  emit { print }
' "$installer_tests" > "$historical_sol"
test -s "$historical_sol" || fail "could not extract the exact v0.4 Sol reviewer fixture"
expected_v040_hash=$(sed -n "s/^v040_sol_reviewer_sha256='\([^']*\)'$/\1/p" "$installer")
test -n "$expected_v040_hash" || fail "installer does not expose the v0.4 Sol migration hash"
if command -v shasum >/dev/null 2>&1; then
  historical_hash=$(shasum -a 256 "$historical_sol" | awk '{print $1}')
else
  historical_hash=$(sha256sum "$historical_sol" | awk '{print $1}')
fi
test "$historical_hash" = "$expected_v040_hash" \
  || fail "extracted v0.4 Sol reviewer does not match the allowlisted migration hash"

missing_state=$tmp_dir/missing-marketplace.state
missing_output=$tmp_dir/missing-marketplace.out
if FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$missing_state" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  CODEX_BIN="$fake_codex" \
  CODEX_HOME="$tmp_dir/missing-marketplace-codex-home" \
  sh "$setup" --check > "$missing_output" 2>&1; then
  fail "setup check accepted a missing marketplace/plugin"
fi
grep -Fq 'FLOC*Loom marketplace floc-studio or enabled plugin floc-loom@floc-studio is missing.' "$missing_output" \
  || fail "missing marketplace refusal is not distinguished"
grep -Fq 'RECOVERY: sh ' "$missing_output" \
  || fail "missing marketplace refusal lacks the canonical setup recovery"

configured_missing_state=$tmp_dir/configured-without-plugin.state
FAKE_CODEX_LOG="$fake_codex_log" \
FAKE_CODEX_STATE="$configured_missing_state" \
FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  "$fake_codex" plugin marketplace add "$default_source" --ref "$default_ref" --json >/dev/null
configured_missing_output=$tmp_dir/configured-without-plugin.out
if FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$configured_missing_state" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  CODEX_BIN="$fake_codex" \
  CODEX_HOME="$tmp_dir/configured-without-plugin-codex-home" \
  sh "$setup" --check > "$configured_missing_output" 2>&1; then
  fail "setup check accepted a configured marketplace with no plugin"
fi
grep -Fq 'marketplace floc-studio is configured, but enabled plugin floc-loom@floc-studio is missing or disabled.' "$configured_missing_output" \
  || fail "configured marketplace/plugin refusal is not distinguished"
pass "missing marketplace and configured-without-plugin recovery paths"

stale_plugin_dir=$tmp_dir/stale-v040-plugin
stale_codex_home=$tmp_dir/stale-v040-codex-home
stale_codex_state=$tmp_dir/stale-v040-marketplace.state
stale_marker=$tmp_dir/stale-installer-ran
stale_check_output=$tmp_dir/stale-setup-check.out
stale_install_output=$tmp_dir/stale-setup-install.out
stale_local_output=$tmp_dir/stale-setup-local.out
stale_add_output=$tmp_dir/stale-marketplace-add.out
mkdir -p "$stale_plugin_dir/.codex-plugin" "$stale_plugin_dir/scripts" "$stale_plugin_dir/agents" "$stale_codex_home/agents"
printf '%s\n' '{"name":"floc-loom","version":"0.4.0"}' > "$stale_plugin_dir/.codex-plugin/plugin.json"
for agent_file in floc-loom-luna-implementer.toml floc-loom-terra-implementer.toml floc-loom-sol-reviewer.toml; do
  case "$agent_file" in
    floc-loom-sol-reviewer.toml) cp "$historical_sol" "$stale_plugin_dir/agents/$agent_file" ;;
    *) cp "$templates/$agent_file" "$stale_plugin_dir/agents/$agent_file" ;;
  esac
  cp "$stale_plugin_dir/agents/$agent_file" "$stale_codex_home/agents/$agent_file"
done
cat > "$stale_plugin_dir/scripts/install-agents.sh" <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' stale-installer-ran > "$STALE_INSTALLER_MARKER"
EOF
chmod +x "$stale_plugin_dir/scripts/install-agents.sh"

run_stale_codex() {
  FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$stale_codex_state" \
  FAKE_PLUGIN_V040_DIR="$stale_plugin_dir" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
    "$fake_codex" "$@"
}

run_stale_setup() {
  FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$stale_codex_state" \
  FAKE_PLUGIN_V040_DIR="$stale_plugin_dir" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  STALE_INSTALLER_MARKER="$stale_marker" \
  CODEX_BIN="$fake_codex" \
  CODEX_HOME="$stale_codex_home" \
    sh "$setup" "$@"
}

# Build a complete stale v0.4 marketplace/plugin/roles/helper state through the fake
# command surface, then prove its ref cannot change until the named marketplace leaves.
run_stale_codex plugin marketplace add "$default_source" --ref v0.4.0 --json >/dev/null
run_stale_codex plugin add floc-loom@floc-studio --json >/dev/null
if run_stale_setup --check > "$stale_check_output" 2>&1; then
  fail "setup check accepted a stale v0.4 plugin"
fi
test ! -e "$stale_marker" || fail "setup check invoked the stale plugin agent installer"
grep -Fq "expected installed FLOC*Loom $default_version before using its companion-agent installer; found 0.4.0." "$stale_check_output" \
  || fail "stale setup refusal did not identify the required manifest"
grep -Fq 'plugin marketplace remove floc-studio' "$stale_check_output" \
  || fail "stale setup refusal lacks the deliberate marketplace removal"
grep -Fq "plugin marketplace add $default_source --ref $default_ref" "$stale_check_output" \
  || fail "stale setup refusal lacks the pinned v0.5 marketplace add"
grep -Fq 'plugin add floc-loom@floc-studio --json' "$stale_check_output" \
  || fail "stale setup refusal lacks the plugin re-add"
if grep -Fq 'UPGRADE:' "$stale_check_output"; then
  fail "stale setup refusal still advertises marketplace upgrade as a recovery"
fi
pass "public_command_surfaces_reject_complete_v040_before_installed_helper"

run_stale_codex plugin marketplace upgrade floc-studio --json >/dev/null
if run_stale_codex plugin marketplace add "$default_source" --ref "$default_ref" --json > "$stale_add_output" 2>&1; then
  fail "fake Codex let marketplace upgrade change a pinned ref"
fi
grep -Fq "marketplace 'floc-studio' is already added from a different source; remove it before adding this source" "$stale_add_output" \
  || fail "fake Codex did not model the ref-transition conflict"

if run_stale_setup > "$stale_install_output" 2>&1; then
  fail "setup install accepted a stale ref-pinned marketplace"
fi
if run_stale_setup --local "$repo_root" > "$stale_local_output" 2>&1; then
  fail "manual fallback accepted a stale ref-pinned marketplace"
fi
test ! -e "$stale_marker" || fail "a stale marketplace refusal invoked the stale plugin agent installer"
for output in "$stale_install_output" "$stale_local_output"; do
  grep -Fq 'plugin marketplace remove floc-studio' "$output" \
    || fail "stale marketplace setup refusal lacks the deliberate transition"
done

# Execute the README's deliberate recovery exactly: remove, add the fixed ref, re-add
# the plugin, then use canonical setup/check to migrate the known v0.4 Sol role.
run_stale_codex plugin marketplace remove floc-studio >/dev/null
run_stale_codex plugin marketplace add "$default_source" --ref "$default_ref" >/dev/null
run_stale_codex plugin add floc-loom@floc-studio --json >/dev/null
run_stale_setup >/dev/null
run_stale_setup --check >/dev/null
test ! -e "$stale_marker" || fail "ref-transition recovery executed the stale helper"
for agent_file in floc-loom-luna-implementer.toml floc-loom-terra-implementer.toml floc-loom-sol-reviewer.toml; do
  cmp -s "$templates/$agent_file" "$stale_codex_home/agents/$agent_file" \
    || fail "ref-transition recovery did not leave a current role: $agent_file"
done
pass "marketplace_ref_transition_recovery_v040_to_v050"

# Recovery output is a separate shell boundary. Exercise a non-default CODEX_BIN and a
# copied setup path with spaces, an apostrophe, and command metacharacters; execute the
# printed commands verbatim in a fake stateful environment and prove no marker ran.
quoted_state=$tmp_dir/quoted-marketplace.state
quoted_codex_home=$tmp_dir/quoted-codex-home
quoted_workdir=$tmp_dir/quoted-recovery-workdir
injected_marker=$quoted_workdir/quoted-command-injected
quoted_stale_marker=$tmp_dir/quoted-stale-installer-ran
injected_marker_name=quoted-command-injected
quoted_codex="$tmp_dir/fake codex's; touch $injected_marker_name; #"
quoted_setup="$tmp_dir/setup script's quote; touch $injected_marker_name; #"
quoted_output=$tmp_dir/quoted-recovery.out
quoted_commands=$tmp_dir/quoted-recovery-commands.sh
quoted_execution_output=$tmp_dir/quoted-recovery-execution.out
quoted_argv_log=$tmp_dir/quoted-recovery-argv.jsonl
mkdir -p "$quoted_workdir"
cp "$fake_codex" "$quoted_codex"
chmod +x "$quoted_codex"
cp "$setup" "$quoted_setup"
chmod +x "$quoted_setup"

run_quoted_codex() (
  cd "$quoted_workdir"
  FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$quoted_state" \
  FAKE_PLUGIN_V040_DIR="$stale_plugin_dir" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  FAKE_CODEX_ARGV_LOG="$quoted_argv_log" \
    "$quoted_codex" "$@"
)

run_quoted_setup() (
  cd "$quoted_workdir"
  FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$quoted_state" \
  FAKE_PLUGIN_V040_DIR="$stale_plugin_dir" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  FAKE_CODEX_ARGV_LOG="$quoted_argv_log" \
  STALE_INSTALLER_MARKER="$quoted_stale_marker" \
  CODEX_BIN="$quoted_codex" \
  CODEX_HOME="$quoted_codex_home" \
    sh "$quoted_setup" "$@"
)

run_quoted_codex plugin marketplace add "$default_source" --ref v0.4.0 --json >/dev/null
run_quoted_codex plugin add floc-loom@floc-studio --json >/dev/null
: > "$quoted_argv_log"
if run_quoted_setup --check > "$quoted_output" 2>&1; then
  fail "quoted-path setup check accepted a stale v0.4 plugin"
fi
test ! -e "$injected_marker" || fail "rendering the stale recovery already injected a marker"
test ! -e "$quoted_stale_marker" || fail "quoted-path setup check invoked the stale helper"

awk '
  /^RECOVERY: / {
    command = substr($0, 11)
    if (command ~ /^sh / || command ~ / plugin marketplace remove / || command ~ / plugin marketplace add / || command ~ / plugin add /) {
      print command
    }
    next
  }
  /^THEN: sh / { print substr($0, 7) }
' "$quoted_output" > "$quoted_commands"
test "$(awk 'END { print NR }' "$quoted_commands")" = 5 \
  || fail "quoted recovery output did not contain the five executable continuation commands"

: > "$quoted_argv_log"
if ! (
  cd "$quoted_workdir"
  FAKE_CODEX_LOG="$fake_codex_log" \
  FAKE_CODEX_STATE="$quoted_state" \
  FAKE_PLUGIN_V040_DIR="$stale_plugin_dir" \
  FAKE_PLUGIN_V050_DIR="$plugin_dir" \
  FAKE_CODEX_ARGV_LOG="$quoted_argv_log" \
  STALE_INSTALLER_MARKER="$quoted_stale_marker" \
  CODEX_BIN="$quoted_codex" \
  CODEX_HOME="$quoted_codex_home" \
  sh "$quoted_commands" > "$quoted_execution_output" 2>&1
); then
  fail "quoted recovery commands did not execute"
fi
test ! -e "$injected_marker" || fail "quoted recovery command execution injected a marker"
test ! -e "$quoted_stale_marker" || fail "quoted recovery command execution invoked the stale helper"
jq -s -e --arg source "$default_source" --arg ref "$default_ref" '
  any(.[]; . == ["plugin", "marketplace", "remove", "floc-studio"])
  and any(.[]; . == ["plugin", "marketplace", "add", $source, "--ref", $ref])
  and any(.[]; . == ["plugin", "add", "floc-loom@floc-studio", "--json"])
' "$quoted_argv_log" >/dev/null \
  || fail "quoted recovery commands did not preserve their intended argv sequences"
pass "recovery_command_paths_are_posix_quoted_and_non_injectable"

# Keep the runtime-inspector's privacy guarantee directly exercised: the emitted object
# is allowlisted and no fixture prompt/token/config/environment content may leak.
runtime_sessions=$tmp_dir/runtime-sessions
runtime_day=$runtime_sessions/2026/08/01
mkdir -p "$runtime_day"
runtime_id=11111111-1111-7111-8111-111111111111
runtime_rollout=$runtime_day/rollout-2026-08-01T00-00-00-$runtime_id.jsonl
printf '%s\n' \
  '{"type":"response_item","payload":{"prompt":"DO_NOT_LEAK_PROMPT","token":"DO_NOT_LEAK_TOKEN"}}' \
  '{"type":"event_msg","payload":{"environment":{"SECRET_ENV":"DO_NOT_LEAK_ENV"},"config":{"api_key":"DO_NOT_LEAK_CONFIG"}}}' \
  "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$runtime_id\",\"parent_thread_id\":\"00000000-0000-7000-8000-000000000000\",\"agent_role\":\"floc_loom_luna_implementer\",\"agent_path\":\"/root/fixture\",\"model_provider\":\"openai\",\"cwd\":\"/fixture/cwd\"}}" \
  '{"type":"turn_context","payload":{"model":"gpt-5.6-luna","effort":"max","sandbox_policy":{"type":"danger-full-access","hidden":"DO_NOT_LEAK_SANDBOX"},"permission_profile":{"type":"disabled","hidden":"DO_NOT_LEAK_PERMISSION"},"cwd":"/fixture/cwd"}}' \
  > "$runtime_rollout"
runtime_output=$(sh "$runtime_inspector" \
  --sessions-dir "$runtime_sessions" \
  --expected-role floc_loom_luna_implementer \
  --expected-model gpt-5.6-luna \
  --expected-effort max \
  --require-sandbox-type danger-full-access \
  --require-permission-profile \
  "$runtime_id")
printf '%s\n' "$runtime_output" | jq -e --arg id "$runtime_id" '
  type == "object"
  and (keys | sort) == ["agent_path", "agent_role", "cwd", "effort", "model", "model_provider", "parent_thread_id", "permission_profile_type", "sandbox_policy_type", "thread_id"]
  and .thread_id == $id
  and .agent_role == "floc_loom_luna_implementer"
  and .model == "gpt-5.6-luna"
  and .effort == "max"
' >/dev/null || fail "runtime inspector did not return the expected safe routing object"
if printf '%s\n' "$runtime_output" | grep -Fq 'DO_NOT_LEAK'; then
  fail "runtime inspector leaked fixture prompt or sensitive runtime content"
fi
if sh "$runtime_inspector" --sessions-dir "$runtime_sessions" --expected-role floc_loom_terra_implementer "$runtime_id" >/dev/null 2>&1; then
  fail "runtime inspector accepted an unexpected role"
fi
pass "runtime inspector allowlisted extraction and strict pin refusal"

sh -n "$installer"
sh -n "$installer_tests"
sh -n "$setup"
sh -n "$runtime_inspector"
sh -n "$script_dir/verify.sh"
pass "shell syntax"

printf '%s\n' "VERIFY PASSED: FLOC*Loom v0.5 route, ledger, review, and installer checks completed"
