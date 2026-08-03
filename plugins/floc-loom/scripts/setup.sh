#!/bin/sh
# Install FLOC*Loom's marketplace plugin and companion custom agents as one flow.

set -eu

plugin_name=floc-loom
marketplace_name=floc-studio
default_source=GsusFC/FLOC-Loom
default_ref=v0.4.0
default_version=0.4.0
codex_bin=${CODEX_BIN:-codex}
source_value=$default_source
ref_value=$default_ref
local_source=''
target_dir=''
check_only=0

usage() {
  cat <<'EOF'
Usage: setup.sh [--local <repo>] [--source <marketplace>] [--ref <git-ref>]
                [--target-dir <agents-dir>] [--check]

Install the pinned FLOC*Loom marketplace release, the plugin, and its three
companion custom-agent profiles in one conflict-safe flow.

Options:
  --local <repo>       Install from a local FLOC*Loom checkout instead of GitHub.
  --source <source>    Marketplace Git source (default: GsusFC/FLOC-Loom).
  --ref <git-ref>      Exact marketplace Git ref (default: v0.4.0).
  --target-dir <path>  Override the Codex custom-agent destination.
  --check              Verify the installed plugin and agents without mutation.
  --help               Show this help text.

The installer never overwrites a differing custom-agent file. Start a new Codex
task after installation so the new native agent types are discovered.
EOF
}

fail() {
  printf '%s\n' "ERROR: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command is unavailable: $1"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --local)
      [ "$#" -ge 2 ] || fail "--local requires a repository path."
      [ -n "$2" ] || fail "--local requires a non-empty repository path."
      local_source=$2
      shift 2
      ;;
    --source)
      [ "$#" -ge 2 ] || fail "--source requires a marketplace source."
      [ -n "$2" ] || fail "--source requires a non-empty marketplace source."
      source_value=$2
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || fail "--ref requires a Git ref."
      [ -n "$2" ] || fail "--ref requires a non-empty Git ref."
      ref_value=$2
      shift 2
      ;;
    --target-dir)
      [ "$#" -ge 2 ] || fail "--target-dir requires a path."
      [ -n "$2" ] || fail "--target-dir requires a non-empty path."
      target_dir=$2
      shift 2
      ;;
    --check)
      check_only=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1 (run with --help for usage)."
      ;;
  esac
done

case "$codex_bin" in
  */*) [ -x "$codex_bin" ] || fail "CODEX_BIN is not executable: $codex_bin" ;;
  *) require_command "$codex_bin" ;;
esac
require_command jq
require_command python3
require_command git
if ! command -v shasum >/dev/null 2>&1 && ! command -v sha256sum >/dev/null 2>&1; then
  fail "required checksum command is unavailable: install shasum or sha256sum"
fi
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
  || fail "Python 3.11 or newer is required."

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in
  /*) ;;
  *) tmp_base=/tmp ;;
esac
setup_tmp=''

cleanup() {
  if [ -n "$setup_tmp" ] && [ -d "$setup_tmp" ]; then
    case "$setup_tmp" in
      "$tmp_base"/floc-loom-setup.*) rm -rf "$setup_tmp" ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $setup_tmp" >&2 ;;
    esac
  fi
}

trap cleanup 0 HUP INT TERM
setup_tmp=$(mktemp -d "$tmp_base/floc-loom-setup.XXXXXX") \
  || fail "could not create a disposable setup directory."
list_json=$setup_tmp/plugin-list.json
marketplace_json=$setup_tmp/marketplace.json
install_json=$setup_tmp/plugin-install.json

run_agent_installer() {
  installed_plugin_dir=$1
  agent_installer=$installed_plugin_dir/scripts/install-agents.sh
  if [ ! -f "$agent_installer" ] || [ -L "$agent_installer" ]; then
    fail "installed plugin is missing its agent installer: $agent_installer"
  fi

  if [ -n "$target_dir" ]; then
    sh "$agent_installer" --target-dir "$target_dir"
    sh "$agent_installer" --target-dir "$target_dir" --check
  else
    sh "$agent_installer"
    sh "$agent_installer" --check
  fi
}

check_agent_installer() {
  installed_plugin_dir=$1
  agent_installer=$installed_plugin_dir/scripts/install-agents.sh
  if [ ! -f "$agent_installer" ] || [ -L "$agent_installer" ]; then
    fail "installed plugin is missing its agent installer: $agent_installer"
  fi

  if [ -n "$target_dir" ]; then
    sh "$agent_installer" --target-dir "$target_dir" --check
  else
    sh "$agent_installer" --check
  fi
}

if [ "$check_only" -eq 1 ]; then
  "$codex_bin" plugin list --json > "$list_json" \
    || fail "could not inspect installed Codex plugins."
  plugin_selector=$plugin_name@$marketplace_name
  installed_count=$(jq -r --arg id "$plugin_selector" \
    '[.installed[] | select(.pluginId == $id and .installed == true and .enabled == true)] | length' \
    "$list_json")
  [ "$installed_count" = "1" ] \
    || fail "expected one enabled $plugin_selector installation; found $installed_count."
  installed_plugin_dir=$(jq -r --arg id "$plugin_selector" \
    '.installed[] | select(.pluginId == $id and .installed == true and .enabled == true) | .source.path' \
    "$list_json")
  [ -d "$installed_plugin_dir" ] \
    || fail "installed plugin path is unavailable: $installed_plugin_dir"
  jq -e --arg name "$plugin_name" '.name == $name and (.version | type == "string")' \
    "$installed_plugin_dir/.codex-plugin/plugin.json" >/dev/null \
    || fail "installed plugin manifest has an unexpected name or version."
  check_agent_installer "$installed_plugin_dir"
  installed_version=$(jq -r '.version' "$installed_plugin_dir/.codex-plugin/plugin.json")
  printf '%s\n' "SETUP CHECK PASSED: FLOC*Loom $installed_version and its companion agents are current."
  exit 0
fi

if [ -n "$local_source" ]; then
  case "$local_source" in
    /*) ;;
    *) local_source=$(pwd -P)/$local_source ;;
  esac
  [ -d "$local_source" ] || fail "local marketplace directory does not exist: $local_source"
  local_source=$(CDPATH='' cd -P "$local_source" && pwd -P) \
    || fail "could not resolve local marketplace directory: $local_source"
  [ -f "$local_source/.agents/plugins/marketplace.json" ] \
    || fail "local path is not a FLOC*Loom marketplace root: $local_source"
  source_value=$local_source
  if ! "$codex_bin" plugin marketplace add "$source_value" --json > "$marketplace_json"; then
    fail "could not add the local FLOC*Loom marketplace."
  fi
else
  case "$source_value" in
    -*) fail "marketplace source must not start with '-': $source_value" ;;
  esac
  case "$ref_value" in
    -*) fail "Git ref must not start with '-': $ref_value" ;;
  esac
  if ! "$codex_bin" plugin marketplace add "$source_value" --ref "$ref_value" --json > "$marketplace_json"; then
    fail "could not add FLOC*Loom marketplace source $source_value at $ref_value."
  fi
fi

reported_marketplace=$(jq -r '.marketplaceName // empty' "$marketplace_json")
[ "$reported_marketplace" = "$marketplace_name" ] \
  || fail "expected marketplace $marketplace_name, but Codex reported ${reported_marketplace:-none}."
plugin_selector=$plugin_name@$marketplace_name

if ! "$codex_bin" plugin add "$plugin_selector" --json > "$install_json"; then
  fail "could not install $plugin_selector."
fi
installed_plugin_dir=$(jq -r '.installedPath // empty' "$install_json")
if [ -z "$installed_plugin_dir" ] || [ ! -d "$installed_plugin_dir" ]; then
  fail "Codex did not report a valid installed plugin path."
fi
jq -e --arg name "$plugin_name" '.name == $name and (.version | type == "string")' \
  "$installed_plugin_dir/.codex-plugin/plugin.json" >/dev/null \
  || fail "installed plugin manifest has an unexpected name or version."
installed_version=$(jq -r '.version' "$installed_plugin_dir/.codex-plugin/plugin.json")
if [ -z "$local_source" ] && [ "$source_value" = "$default_source" ] \
  && [ "$ref_value" = "$default_ref" ] && [ "$installed_version" != "$default_version" ]; then
  fail "expected FLOC*Loom $default_version from $default_ref, but Codex installed $installed_version; inspect the configured marketplace before continuing."
fi

run_agent_installer "$installed_plugin_dir"

printf '%s\n' "SETUP PASSED: FLOC*Loom $installed_version and its companion agents are installed."
printf '%s\n' "NEXT: start a new Codex task, select GPT-5.6 Sol with High reasoning, and invoke FLOC*Loom."
