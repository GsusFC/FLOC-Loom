#!/bin/sh
# Install FLOC*Loom custom-agent templates without changing Codex configuration.

set -eu

usage() {
  cat <<'EOF'
Usage: install-agents.sh [--target-dir <path>] [--check | --check-role <luna|terra|sol>]

Install FLOC*Loom's custom-agent templates into the target directory. Without
--target-dir, the target is "$CODEX_HOME/agents" when CODEX_HOME is already set,
otherwise "$HOME/.codex/agents". The script never overwrites an arbitrary differing
file. It may replace only an allowlisted byte-exact historical FLOC*Loom template.

Options:
  --target-dir <path>  Explicit destination directory (absolute or relative).
  --check              Verify every destination file exactly matches the current
                       shipped template; do not create, copy, or migrate anything.
  --check-role <role>  Role-scoped exactness preflight for luna, terra, or sol;
                       implies --check and does not inspect other roles.
  --help               Show this help text.
EOF
}

fail() {
  printf '%s\n' "ERROR: $*" >&2
  exit 1
}

# This SHA-256 identifies the v0.4.0 shipped Sol reviewer template. A hash match is
# an allowlist entry, not a general "old file" heuristic: any other differing user
# file remains a conflict and is never overwritten.
v040_sol_reviewer_sha256='a04b56ea3953c9192129a83442ddebdf5fbae4289a0f47b7a1643312b628bd4f'

hash_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    fail "cannot identify an allowlisted historical template because shasum and sha256sum are unavailable"
  fi
}

role_file() {
  case "$1" in
    luna) printf '%s\n' 'floc-loom-luna-implementer.toml' ;;
    terra) printf '%s\n' 'floc-loom-terra-implementer.toml' ;;
    sol) printf '%s\n' 'floc-loom-sol-reviewer.toml' ;;
    *) fail "unknown role: $1" ;;
  esac
}

# Reject symlinks in every currently existing parent segment. We intentionally do not
# canonicalize through a symlink: doing so would hide the very condition the installer
# must refuse. Call again immediately before each mutation to narrow TOCTOU exposure.
assert_safe_parent_chain() {
  candidate=$(dirname "$1")
  while [ "$candidate" != '/' ]; do
    if [ -L "$candidate" ]; then
      fail "refusing to use a symlink in an agent target parent: $candidate"
    fi
    if [ -e "$candidate" ] && [ ! -d "$candidate" ]; then
      fail "agent target parent is not a directory: $candidate"
    fi
    candidate=$(dirname "$candidate")
  done
}

assert_safe_target_directory() {
  assert_safe_parent_chain "$target_dir"
  if [ -L "$target_dir" ]; then
    fail "refusing to use a symlink as an agent target directory: $target_dir"
  fi
  if [ -e "$target_dir" ] && [ ! -d "$target_dir" ]; then
    fail "target directory is not a real directory: $target_dir"
  fi
}

is_allowlisted_historical_template() {
  role=$1
  destination=$2
  case "$role" in
    sol) [ "$(hash_file "$destination")" = "$v040_sol_reviewer_sha256" ] ;;
    *) return 1 ;;
  esac
}

# Set destination_state to one of exact, missing, migrate, or conflict. All callers
# have already checked the parent chain, and symlinks are always a hard conflict.
classify_destination() {
  role=$1
  template=$2
  destination=$3
  destination_state=''

  if [ -L "$destination" ]; then
    destination_state='conflict'
  elif [ -e "$destination" ]; then
    if [ ! -f "$destination" ]; then
      destination_state='conflict'
    elif cmp -s "$template" "$destination"; then
      destination_state='exact'
    elif is_allowlisted_historical_template "$role" "$destination"; then
      destination_state='migrate'
    else
      destination_state='conflict'
    fi
  else
    destination_state='missing'
  fi
}

remove_staged() {
  staged=$1
  if [ -n "$staged" ] && [ -e "$staged" ]; then
    rm -f "$staged" || fail "could not remove staged template: $staged"
  fi
}

install_missing() {
  role=$1
  template=$2
  destination=$3
  staged=''

  assert_safe_parent_chain "$destination"
  [ ! -L "$destination" ] || fail "destination became a symlink after preflight and will not be replaced: $destination"
  classify_destination "$role" "$template" "$destination"
  case "$destination_state" in
    missing) ;;
    exact) printf '%s\n' "ALREADY CURRENT: $destination"; return ;;
    *) fail "destination changed after preflight and will not be installed: $destination" ;;
  esac

  staged=$(mktemp "$target_dir/.floc-loom-agent.XXXXXX") || fail "could not stage template for installation: $destination"
  if ! cp "$template" "$staged"; then
    remove_staged "$staged"
    fail "could not stage template for installation: $destination"
  fi
  cmp -s "$template" "$staged" || {
    remove_staged "$staged"
    fail "staged template did not remain byte-exact: $destination"
  }

  assert_safe_parent_chain "$destination"
  [ ! -L "$destination" ] || {
    remove_staged "$staged"
    fail "destination became a symlink after preflight and will not be replaced: $destination"
  }
  if ln "$staged" "$destination"; then
    remove_staged "$staged"
  else
    remove_staged "$staged"
    if [ -f "$destination" ] && [ ! -L "$destination" ] && cmp -s "$template" "$destination"; then
      printf '%s\n' "ALREADY CURRENT: $destination"
      return
    fi
    fail "destination changed after preflight and will not be installed: $destination"
  fi

  if ! { [ -f "$destination" ] && [ ! -L "$destination" ] && cmp -s "$template" "$destination"; }; then
    fail "post-install exactness check failed: $destination"
  fi
  printf '%s\n' "INSTALLED: $destination"
}

migrate_historical() {
  role=$1
  template=$2
  destination=$3
  staged=''

  # Reclassify immediately before replacement. The allowlist check is repeated after
  # staging so an arbitrary edit made after global preflight is never overwritten.
  assert_safe_parent_chain "$destination"
  [ ! -L "$destination" ] || fail "destination became a symlink after preflight and will not be migrated: $destination"
  classify_destination "$role" "$template" "$destination"
  case "$destination_state" in
    migrate) ;;
    exact) printf '%s\n' "ALREADY CURRENT: $destination"; return ;;
    *) fail "destination changed after preflight and will not be migrated: $destination" ;;
  esac

  staged=$(mktemp "$target_dir/.floc-loom-agent.XXXXXX") || fail "could not stage historical migration: $destination"
  if ! cp "$template" "$staged"; then
    remove_staged "$staged"
    fail "could not stage historical migration: $destination"
  fi
  cmp -s "$template" "$staged" || {
    remove_staged "$staged"
    fail "staged migration did not remain byte-exact: $destination"
  }

  assert_safe_parent_chain "$destination"
  [ ! -L "$destination" ] || {
    remove_staged "$staged"
    fail "destination became a symlink after preflight and will not be migrated: $destination"
  }
  classify_destination "$role" "$template" "$destination"
  case "$destination_state" in
    migrate) ;;
    exact)
      remove_staged "$staged"
      printf '%s\n' "ALREADY CURRENT: $destination"
      return
      ;;
    *)
      remove_staged "$staged"
      fail "destination changed after preflight and will not be migrated: $destination"
      ;;
  esac

  # mv/rename replaces the destination entry atomically; it does not copy through a
  # destination symlink. We checked regular-file and allowlisted-byte identity just
  # above and verify the final replacement is regular and byte-exact below.
  if ! mv -f "$staged" "$destination"; then
    remove_staged "$staged"
    fail "could not atomically migrate historical template: $destination"
  fi
  if ! { [ -f "$destination" ] && [ ! -L "$destination" ] && cmp -s "$template" "$destination"; }; then
    fail "post-migration exactness check failed: $destination"
  fi
  printf '%s\n' "MIGRATED: $destination"
}

script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd) || exit 1
template_dir=$script_dir/../agents
target_dir=''
check_only=0
check_role=''

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target-dir)
      [ "$#" -ge 2 ] || fail "--target-dir requires a path."
      [ -n "$2" ] || fail "--target-dir requires a non-empty path."
      case "$2" in
        --*) fail "--target-dir path must be explicit; prefix a relative option-like name with ./ or use an absolute path." ;;
      esac
      target_dir=$2
      shift 2
      ;;
    --check)
      [ -z "$check_role" ] || fail "--check and --check-role are mutually exclusive."
      check_only=1
      shift
      ;;
    --check-role)
      [ "$#" -ge 2 ] || fail "--check-role requires luna, terra, or sol."
      [ -z "$check_role" ] || fail "--check-role may be specified only once."
      [ "$check_only" -eq 0 ] || fail "--check and --check-role are mutually exclusive."
      case "$2" in
        luna|terra|sol) check_role=$2 ;;
        *) fail "--check-role must be luna, terra, or sol." ;;
      esac
      check_only=1
      shift 2
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

# Resolve the default only after parsing options so an explicit target works even when
# HOME and CODEX_HOME are unset.
if [ -z "$target_dir" ]; then
  if [ -n "${CODEX_HOME-}" ]; then
    target_dir=$CODEX_HOME/agents
  else
    [ -n "${HOME-}" ] || fail "HOME is unset and CODEX_HOME was not supplied; pass --target-dir explicitly."
    target_dir=$HOME/.codex/agents
  fi
fi

case "$target_dir" in
  /*) ;;
  *) target_dir=$(pwd -P)/$target_dir ;;
esac
# macOS commonly exposes a physical temporary directory through the stable system
# aliases /tmp and /var. Normalize only those root aliases before enforcing the
# parent-symlink refusal below; every caller-supplied parent segment that remains is
# still checked and rejected if it is a symlink. This keeps explicit mktemp/TMPDIR
# fixture targets usable without allowing a user-created parent redirect.
case "$target_dir" in
  /tmp|/tmp/*)
    target_suffix=${target_dir#/tmp}
    target_dir=$(CDPATH='' cd -P /tmp && pwd -P)$target_suffix || fail "could not resolve the system temporary directory"
    ;;
  /var|/var/*)
    target_suffix=${target_dir#/var}
    target_dir=$(CDPATH='' cd -P /var && pwd -P)$target_suffix || fail "could not resolve the system variable directory"
    ;;
esac
while [ "$target_dir" != '/' ] && [ "${target_dir%/}" != "$target_dir" ]; do
  target_dir=${target_dir%/}
done
case "/$target_dir/" in
  */../*) fail "target directory must not contain a parent traversal: $target_dir" ;;
esac
[ "$target_dir" != '/' ] || fail "refusing to use the filesystem root as an agent target directory."

if [ -n "$check_role" ]; then
  selected_roles=$check_role
else
  selected_roles='luna terra sol'
fi

# Validate all selected shipped sources before looking at or mutating destinations.
for role in $selected_roles; do
  agent_file=$(role_file "$role")
  template=$template_dir/$agent_file
  if [ ! -f "$template" ] || [ -L "$template" ]; then
    fail "shipped template is missing or not a regular file: $template"
  fi
done

# Preflight every intended destination before creating a directory or changing a file.
assert_safe_target_directory
preflight_failed=0
for role in $selected_roles; do
  agent_file=$(role_file "$role")
  template=$template_dir/$agent_file
  destination=$target_dir/$agent_file
  classify_destination "$role" "$template" "$destination"
  case "$destination_state" in
    exact) ;;
    missing)
      if [ "$check_only" -eq 1 ]; then
        printf '%s\n' "ERROR: required installed $role agent file is missing: $destination" >&2
        printf '%s\n' "       Run $0 without --check after reviewing the target directory." >&2
        preflight_failed=1
      fi
      ;;
    migrate)
      if [ "$check_only" -eq 1 ]; then
        printf '%s\n' "ERROR: installed $role agent file is an allowlisted historical template and requires migration: $destination" >&2
        printf '%s\n' "       Run $0 without --check to migrate this exact shipped version." >&2
        preflight_failed=1
      fi
      ;;
    conflict)
      if [ -L "$destination" ]; then
        printf '%s\n' "ERROR: destination is a symlink and will not be replaced: $destination" >&2
      elif [ -e "$destination" ] && [ ! -f "$destination" ]; then
        printf '%s\n' "ERROR: destination is not a regular file and will not be replaced: $destination" >&2
      else
        printf '%s\n' "ERROR: destination differs from the shipped template and is not an allowlisted historical version: $destination" >&2
        printf '%s\n' "       Inspect $template and resolve the conflict deliberately, then rerun --check." >&2
      fi
      preflight_failed=1
      ;;
    *) fail "internal error: unknown destination preflight state: $destination_state" ;;
  esac
done
[ "$preflight_failed" -eq 0 ] || exit 1

if [ "$check_only" -eq 1 ]; then
  if [ -n "$check_role" ]; then
    printf '%s\n' "CHECK PASSED: FLOC*Loom $check_role agent file exactly matches $template_dir."
  else
    printf '%s\n' "CHECK PASSED: all FLOC*Loom agent files exactly match $template_dir."
  fi
  exit 0
fi

# The full conflict preflight passed. Create the directory only now, then revalidate
# parent safety before every creation or replacement.
if [ ! -d "$target_dir" ]; then
  assert_safe_parent_chain "$target_dir"
  mkdir -p "$target_dir" || fail "could not create target directory: $target_dir"
fi
assert_safe_target_directory

for role in $selected_roles; do
  agent_file=$(role_file "$role")
  template=$template_dir/$agent_file
  destination=$target_dir/$agent_file
  classify_destination "$role" "$template" "$destination"
  case "$destination_state" in
    exact) printf '%s\n' "ALREADY CURRENT: $destination" ;;
    missing) install_missing "$role" "$template" "$destination" ;;
    migrate) migrate_historical "$role" "$template" "$destination" ;;
    *) fail "destination changed after preflight and will not be replaced: $destination" ;;
  esac
done

for role in $selected_roles; do
  agent_file=$(role_file "$role")
  template=$template_dir/$agent_file
  destination=$target_dir/$agent_file
  if ! { [ -f "$destination" ] && [ ! -L "$destination" ] && cmp -s "$template" "$destination"; }; then
    fail "post-install exactness check failed: $destination"
  fi
done

printf '%s\n' "INSTALL PASSED: selected FLOC*Loom agent files exactly match $template_dir."
