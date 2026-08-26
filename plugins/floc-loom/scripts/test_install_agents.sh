#!/bin/sh
# Disposable regression fixtures for install-agents.sh.

set -eu

pass() {
  printf '%s\n' "PASS: $*"
}

fail() {
  printf '%s\n' "FAIL: $*" >&2
  exit 1
}

script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd) || exit 1
installer=$script_dir/install-agents.sh
templates=$script_dir/../agents

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in
  /*) ;;
  *) tmp_base=/tmp ;;
esac
tmp_base=$(CDPATH='' cd -P "$tmp_base" && pwd -P) || fail "could not resolve fixture temporary directory"
tmp_dir=''

cleanup() {
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    case "$tmp_dir" in
      "$tmp_base"/floc-loom-install-test.*) rm -rf "$tmp_dir" ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
    esac
  fi
}
trap cleanup 0 HUP INT TERM

tmp_dir=$(mktemp -d "$tmp_base/floc-loom-install-test.XXXXXX") || fail "could not create fixture directory"

write_v040_sol_reviewer() {
  cat > "$1" <<'EOF'
name = "floc_loom_sol_reviewer"
description = "FLOC*Loom's fresh, read-only final review lane for inspected diffs and evidence."
model = "gpt-5.6-sol"
model_reasoning_effort = "high"
sandbox_mode = "read-only"

developer_instructions = """
You are FLOC*Loom's fresh final reviewer. Remain strictly read-only: do not create,
modify, delete, format, or implement files, and do not broaden the requested scope.
Inspect the actual files, accumulated change set, stated interfaces and constraints,
    and verification evidence in a fresh context.
    Report the observed sandbox policy and permission profile exactly when they are
    available; the requested TOML sandbox is not proof of host-enforced isolation.

    Return exactly one verdict: ship, fix-first, or rethink. Base the verdict on concrete,
evidence-backed findings. Use fix-first only for bounded required corrections and
rethink when the architecture or scope must change. Do not silently substitute a
different role, model, or reasoning level; this installed custom-agent profile is the
required read-only review lane.
"""
EOF
}

for file in floc-loom-luna-implementer.toml floc-loom-terra-implementer.toml floc-loom-sol-reviewer.toml; do
  test -f "$templates/$file" || fail "template missing: $file"
done

clean=$tmp_dir/clean
sh "$installer" --target-dir "$clean"
for role in luna terra sol; do
  sh "$installer" --target-dir "$clean" --check-role "$role"
done
sh "$installer" --target-dir "$clean" --check
pass "all-role and role-scoped exactness checks"

role_scoped=$tmp_dir/role-scoped
mkdir "$role_scoped"
printf '%s\n' 'user-owned Luna customization' > "$role_scoped/floc-loom-luna-implementer.toml"
cp "$templates/floc-loom-sol-reviewer.toml" "$role_scoped/floc-loom-sol-reviewer.toml"
sh "$installer" --target-dir "$role_scoped" --check-role sol
if sh "$installer" --target-dir "$role_scoped" --check-role luna >/dev/null 2>&1; then
  fail "role-scoped Luna check accepted a modified Luna file"
fi
pass "role-scoped check does not inspect unrelated roles"

migration=$tmp_dir/migration
mkdir "$migration"
old_sol=$tmp_dir/v040-sol-reviewer.toml
write_v040_sol_reviewer "$old_sol"
cp "$old_sol" "$migration/floc-loom-sol-reviewer.toml"
if sh "$installer" --target-dir "$migration" --check-role sol >/dev/null 2>&1; then
  fail "role-scoped check accepted an exact v0.4 Sol template without migration"
fi
sh "$installer" --target-dir "$migration" > "$tmp_dir/migration.out"
grep -Fq "MIGRATED: $migration/floc-loom-sol-reviewer.toml" "$tmp_dir/migration.out" \
  || fail "installer did not report the allowlisted historical migration"
for file in floc-loom-luna-implementer.toml floc-loom-terra-implementer.toml floc-loom-sol-reviewer.toml; do
  cmp -s "$templates/$file" "$migration/$file" || fail "migration final copy is not byte-exact: $file"
done
pass "exact v0.4 Sol reviewer migration and byte-exact final copies"

modified=$tmp_dir/modified
mkdir "$modified"
printf '%s\n' 'user-owned modified Sol reviewer' > "$modified/floc-loom-sol-reviewer.toml"
if sh "$installer" --target-dir "$modified" >/dev/null 2>&1; then
  fail "installer overwrote a modified Sol reviewer"
fi
grep -Fq 'user-owned modified Sol reviewer' "$modified/floc-loom-sol-reviewer.toml" \
  || fail "modified Sol reviewer content changed"
test ! -e "$modified/floc-loom-luna-implementer.toml" || fail "modified-file refusal installed Luna despite preflight conflict"
test ! -e "$modified/floc-loom-terra-implementer.toml" || fail "modified-file refusal installed Terra despite preflight conflict"
pass "modified-file refusal without arbitrary overwrite"

zero_mutation=$tmp_dir/zero-mutation
mkdir "$zero_mutation"
cp "$old_sol" "$zero_mutation/floc-loom-sol-reviewer.toml"
printf '%s\n' 'user-owned Terra customization' > "$zero_mutation/floc-loom-terra-implementer.toml"
if sh "$installer" --target-dir "$zero_mutation" >/dev/null 2>&1; then
  fail "installer accepted a multi-role preflight conflict"
fi
cmp -s "$old_sol" "$zero_mutation/floc-loom-sol-reviewer.toml" \
  || fail "conflicting preflight migrated Sol before refusing the Terra conflict"
test ! -e "$zero_mutation/floc-loom-luna-implementer.toml" \
  || fail "conflicting preflight installed Luna before refusing the Terra conflict"
grep -Fq 'user-owned Terra customization' "$zero_mutation/floc-loom-terra-implementer.toml" \
  || fail "conflicting Terra file changed"
pass "all intended mutations are preflighted before a conflict produces zero mutation"

destination_symlink=$tmp_dir/destination-symlink
mkdir "$destination_symlink"
printf '%s\n' 'outside destination' > "$tmp_dir/outside.toml"
ln -s "$tmp_dir/outside.toml" "$destination_symlink/floc-loom-sol-reviewer.toml"
if sh "$installer" --target-dir "$destination_symlink" >/dev/null 2>&1; then
  fail "installer accepted a destination symlink"
fi
test -L "$destination_symlink/floc-loom-sol-reviewer.toml" || fail "destination symlink changed"
pass "destination symlink refusal"

real_parent=$tmp_dir/real-parent
mkdir "$real_parent"
ln -s "$real_parent" "$tmp_dir/parent-link"
if sh "$installer" --target-dir "$tmp_dir/parent-link/agents" >/dev/null 2>&1; then
  fail "installer accepted a parent symlink"
fi
test ! -e "$real_parent/agents" || fail "parent symlink refusal mutated the real target"
pass "parent symlink refusal"

printf '%s\n' "INSTALLER TESTS PASSED: role checks, exact v0.4 migration, conflict preflight, and symlink refusals"
