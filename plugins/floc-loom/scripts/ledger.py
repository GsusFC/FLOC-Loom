#!/usr/bin/env python3
"""Fail-closed execution ledger for FLOC*Loom runs.

The Codex host remains responsible for spawning native agents. This ledger makes
the evidence needed for acceptance explicit and machine-checkable: observed role
pins, verification results, review metadata, read-only state snapshots, and the
allowed file set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ROLE_PINS = {
    "floc_loom_luna_implementer": {"model": "gpt-5.6-luna", "effort": "max"},
    "floc_loom_terra_implementer": {"model": "gpt-5.6-terra", "effort": "max"},
    "floc_loom_sol_reviewer": {"model": "gpt-5.6-sol", "effort": "high"},
}
REVIEW_ROLE = "floc_loom_sol_reviewer"


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"ERROR: {message}")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        fail(f"cannot hash evidence file {path}: {exc}")
    return digest.hexdigest()


def write_json(path: Path, value: Any, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = canonical_json(value) + b"\n"
    if exclusive:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            fail(f"refusing to overwrite existing ledger artifact: {path}")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
        except OSError as exc:
            fail(f"cannot write ledger artifact {path}: {exc}")
        return

    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        fail(f"cannot write ledger artifact {path}: {exc}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid or unreadable ledger artifact {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"ledger artifact must contain a JSON object: {path}")
    return value


def canonical_repo(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"not a readable Git repository: {path} ({exc})")
    reported = Path(result.stdout.strip()).resolve()
    if reported != path:
        path = reported
    return path


def git_bytes(repo: Path, arguments: list[str]) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"Git command failed in {repo}: {' '.join(arguments)} ({exc})")
    return result.stdout


def git_text(repo: Path, arguments: list[str]) -> str:
    return git_bytes(repo, arguments).decode("utf-8", errors="surrogateescape").strip()


def validate_uuid(value: str, label: str) -> str:
    if not UUID_RE.fullmatch(value):
        fail(f"{label} must be a lowercase canonical UUID")
    return value


def normalize_owned_file(repo: Path, raw: str) -> str:
    if not raw:
        fail("--owned-file cannot be empty")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = repo / candidate
    candidate = candidate.resolve(strict=False)
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        fail(f"owned file is outside the repository: {raw}")
    if str(relative) in ("", "."):
        fail("--owned-file must identify a file or directory below the repository")
    return relative.as_posix()


def file_digest(path: Path) -> dict[str, str | None]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing", "sha256": None}
    except OSError as exc:
        fail(f"cannot inspect repository path {path}: {exc}")

    if stat.S_ISLNK(metadata.st_mode):
        target = os.fsencode(os.readlink(path))
        return {"kind": "symlink", "sha256": sha256_bytes(b"symlink\0" + target)}
    if stat.S_ISREG(metadata.st_mode):
        return {"kind": "file", "sha256": sha256_file(path)}
    if stat.S_ISDIR(metadata.st_mode):
        return {"kind": "directory", "sha256": None}
    return {"kind": "other", "sha256": None}


def tracked_and_untracked_paths(repo: Path) -> list[str]:
    raw = git_bytes(repo, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"])
    paths = {os.fsdecode(item) for item in raw.split(b"\0") if item}
    return sorted(paths)


def make_snapshot(repo: Path) -> dict[str, Any]:
    files = {path: file_digest(repo / path) for path in tracked_and_untracked_paths(repo)}
    core = {
        "schema_version": SCHEMA_VERSION,
        "git_head": git_text(repo, ["rev-parse", "HEAD"]),
        "status_sha256": sha256_bytes(git_bytes(repo, ["status", "--porcelain=v1", "--untracked-files=all", "-z"])),
        "diff_sha256": sha256_bytes(git_bytes(repo, ["diff", "--binary", "--no-ext-diff", "HEAD"])),
        "files": files,
    }
    return {**core, "captured_at": now(), "snapshot_hash": sha256_bytes(canonical_json(core))}


def validate_snapshot(value: dict[str, Any], path: Path) -> None:
    required = {"schema_version", "git_head", "status_sha256", "diff_sha256", "files", "snapshot_hash"}
    if not required.issubset(value):
        fail(f"snapshot is missing required fields: {path}")
    core = {key: value[key] for key in ("schema_version", "git_head", "status_sha256", "diff_sha256", "files")}
    if value["snapshot_hash"] != sha256_bytes(canonical_json(core)):
        fail(f"snapshot hash mismatch: {path}")


def load_run(ledger: Path) -> dict[str, Any]:
    ledger = ledger.resolve()
    run = read_json(ledger / "run.json")
    if run.get("schema_version") != SCHEMA_VERSION:
        fail(f"unsupported ledger schema in {ledger / 'run.json'}")
    validate_uuid(str(run.get("run_id", "")), "run_id")
    repo = canonical_repo(str(run.get("repo", "")))
    if str(repo) != str(Path(run["repo"]).resolve()):
        fail("ledger repository path changed after initialization")
    return run


def default_ledger_root() -> Path:
    explicit = os.environ.get("FLOC_LOOM_RUNS_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return (Path(codex_home).expanduser() / "floc-loom" / "runs").resolve()
    home = os.environ.get("HOME")
    if home:
        return (Path(home).expanduser() / ".codex" / "floc-loom" / "runs").resolve()
    fail("HOME and CODEX_HOME are unset; pass --ledger-root explicitly")


def cmd_init(args: argparse.Namespace) -> None:
    repo = canonical_repo(args.repo)
    run_id = validate_uuid(args.run_id, "run_id")
    if not args.owned_file:
        fail("at least one --owned-file is required")
    owned = sorted({normalize_owned_file(repo, item) for item in args.owned_file})
    root = Path(args.ledger_root).expanduser().resolve() if args.ledger_root else default_ledger_root()
    run_dir = root / run_id
    if run_dir.exists():
        fail(f"ledger run already exists: {run_dir}")
    initial = make_snapshot(repo)
    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "repo": str(repo),
        "created_at": now(),
        "base_commit": initial["git_head"],
        "owned_files": owned,
        "review_policy": {"requires_hard_isolation": True},
    }
    try:
        run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
        write_json(run_dir / "run.json", run, exclusive=True)
        write_json(run_dir / "initial-state.json", initial, exclusive=True)
        (run_dir / "workers").mkdir(mode=0o700)
        (run_dir / "verifications").mkdir(mode=0o700)
    except OSError as exc:
        fail(f"could not create ledger run {run_dir}: {exc}")
    print(f"LEDGER INITIALIZED: {run_dir}")


def require_worker_pin(role: str, model: str, effort: str) -> None:
    expected = ROLE_PINS.get(role)
    if expected is None or role == REVIEW_ROLE:
        fail(f"role is not an implementation lane: {role}")
    if model != expected["model"] or effort != expected["effort"]:
        fail(f"role pin mismatch for {role}: expected {expected['model']}/{expected['effort']}")


def require_review_pin(role: str, model: str, effort: str) -> None:
    expected = ROLE_PINS[REVIEW_ROLE]
    if role != REVIEW_ROLE or model != expected["model"] or effort != expected["effort"]:
        fail(f"review pin mismatch: expected {REVIEW_ROLE} {expected['model']}/{expected['effort']}")


def common_runtime_fields(args: argparse.Namespace) -> dict[str, Any]:
    validate_uuid(args.thread_id, "thread_id")
    if not args.cwd:
        fail("--cwd is required")
    return {
        "thread_id": args.thread_id,
        "agent_role": args.role,
        "model": args.model,
        "effort": args.effort,
        "cwd": args.cwd,
        "agent_path": args.agent_path,
        "model_provider": args.model_provider,
        "sandbox_policy_type": args.sandbox_policy_type,
        "permission_profile_type": args.permission_profile_type,
        "recorded_at": now(),
    }


def cmd_record_worker(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    load_run(ledger)
    require_worker_pin(args.role, args.model, args.effort)
    record = common_runtime_fields(args)
    write_json(ledger / "workers" / f"{args.thread_id}.json", record, exclusive=True)
    print(f"WORKER RECORDED: {args.thread_id}")


def cmd_record_verification(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    load_run(ledger)
    evidence = Path(args.evidence_file).expanduser().resolve()
    if not evidence.is_file():
        fail(f"verification evidence file is unavailable: {evidence}")
    if args.exit_code < 0:
        fail("--exit-code cannot be negative")
    record = {
        "schema_version": SCHEMA_VERSION,
        "command": args.command,
        "exit_code": args.exit_code,
        "evidence_file": str(evidence),
        "evidence_sha256": sha256_file(evidence),
        "recorded_at": now(),
    }
    write_json(ledger / "verifications" / f"{uuid.uuid4()}.json", record, exclusive=True)
    print(f"VERIFICATION RECORDED: {args.command}")


def cmd_snapshot(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    if args.label not in {"before-review", "after-review"}:
        fail("snapshot label must be before-review or after-review")
    repo = canonical_repo(str(run["repo"]))
    target = ledger / f"{args.label}.json"
    write_json(target, make_snapshot(repo), exclusive=True)
    print(f"SNAPSHOT RECORDED: {args.label}")


def cmd_record_review(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    require_review_pin(args.role, args.model, args.effort)
    if not args.sandbox_policy_type:
        fail("review requires observed sandbox policy type")
    if not args.permission_profile_type:
        fail("review requires observed permission profile type")
    if not args.reason:
        fail("review requires an evidence-based reason")
    if not args.residual_risk:
        fail("review requires residual-risk reporting")
    before_path = ledger / "before-review.json"
    after_path = ledger / "after-review.json"
    before = read_json(before_path)
    after = read_json(after_path)
    validate_snapshot(before, before_path)
    validate_snapshot(after, after_path)
    validate_uuid(args.thread_id, "thread_id")
    record = {
        "schema_version": SCHEMA_VERSION,
        "thread_id": args.thread_id,
        "agent_role": args.role,
        "model": args.model,
        "effort": args.effort,
        "cwd": args.cwd,
        "agent_path": args.agent_path,
        "model_provider": args.model_provider,
        "sandbox_policy_type": args.sandbox_policy_type,
        "permission_profile_type": args.permission_profile_type,
        "verdict": args.verdict,
        "reason": args.reason,
        "residual_risk": args.residual_risk,
        "before_snapshot_hash": before["snapshot_hash"],
        "after_snapshot_hash": after["snapshot_hash"],
        "recorded_at": now(),
    }
    write_json(ledger / "review.json", record, exclusive=True)
    print(f"REVIEW RECORDED: {args.verdict}")


def changed_paths(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_files = before.get("files", {})
    after_files = after.get("files", {})
    paths = set(before_files) | set(after_files)
    return sorted(path for path in paths if before_files.get(path) != after_files.get(path))


def load_artifacts(ledger: Path, directory: str) -> list[dict[str, Any]]:
    folder = ledger / directory
    if not folder.is_dir():
        return []
    artifacts = []
    for path in sorted(folder.glob("*.json")):
        artifacts.append(read_json(path))
    return artifacts


def cmd_accept(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    initial_path = ledger / "initial-state.json"
    before_path = ledger / "before-review.json"
    after_path = ledger / "after-review.json"
    review_path = ledger / "review.json"
    initial = read_json(initial_path)
    before = read_json(before_path)
    after = read_json(after_path)
    review = read_json(review_path)
    validate_snapshot(initial, initial_path)
    validate_snapshot(before, before_path)
    validate_snapshot(after, after_path)

    workers = load_artifacts(ledger, "workers")
    if not workers:
        fail("no implementation worker evidence was recorded")
    worker_ids: set[str] = set()
    for worker in workers:
        thread_id = validate_uuid(str(worker.get("thread_id", "")), "worker thread_id")
        if thread_id in worker_ids:
            fail(f"duplicate worker thread id: {thread_id}")
        worker_ids.add(thread_id)
        require_worker_pin(str(worker.get("agent_role", "")), str(worker.get("model", "")), str(worker.get("effort", "")))
        if not worker.get("cwd"):
            fail(f"worker evidence is missing cwd: {thread_id}")

    verifications = load_artifacts(ledger, "verifications")
    if not verifications:
        fail("no verification evidence was recorded")
    for verification in verifications:
        if not isinstance(verification.get("exit_code"), int) or verification["exit_code"] != 0:
            fail(f"verification did not pass: {verification.get('command', '<unknown>')}")
        evidence = Path(str(verification.get("evidence_file", "")))
        if not evidence.is_file():
            fail(f"verification evidence file disappeared: {evidence}")
        if sha256_file(evidence) != verification.get("evidence_sha256"):
            fail(f"verification evidence changed: {evidence}")

    require_review_pin(str(review.get("agent_role", "")), str(review.get("model", "")), str(review.get("effort", "")))
    validate_uuid(str(review.get("thread_id", "")), "review thread_id")
    if not review.get("cwd"):
        fail("review evidence is missing cwd")
    if not review.get("reason"):
        fail("review evidence is missing reason")
    if not review.get("residual_risk"):
        fail("review evidence is missing residual risk")
    if review.get("verdict") != "ship":
        fail(f"final Sol review is not ship: {review.get('verdict')}")
    if not review.get("permission_profile_type"):
        fail("review evidence is missing permission profile type")
    if not review.get("sandbox_policy_type"):
        fail("review evidence is missing sandbox policy type")
    if review.get("before_snapshot_hash") != before["snapshot_hash"] or review.get("after_snapshot_hash") != after["snapshot_hash"]:
        fail("review does not reference the recorded before/after snapshots")
    if before["snapshot_hash"] != after["snapshot_hash"]:
        fail("review changed repository/artifact state; read-only acceptance failed")

    hard_isolation = review["sandbox_policy_type"] == "read-only"
    if not hard_isolation:
        if not args.allow_behavioral_read_only:
            fail("review sandbox was not observed as read-only; pass --allow-behavioral-read-only only when hard isolation is not required")
        if str(review.get("residual_risk", "")).strip().lower() in {"", "none", "none."}:
            fail("behavioral read-only acceptance requires explicit residual-risk reporting")

    repo = canonical_repo(str(run["repo"]))
    current = make_snapshot(repo)
    if current["snapshot_hash"] != after["snapshot_hash"]:
        fail("repository changed after the after-review snapshot")

    owned_files = set(run.get("owned_files", []))
    out_of_scope = [
        path
        for path in changed_paths(initial, current)
        if not any(path == owned or path.startswith(f"{owned}/") for owned in owned_files)
    ]
    if out_of_scope:
        fail("out-of-scope files changed: " + ", ".join(out_of_scope))

    acceptance = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run["run_id"],
        "accepted_at": now(),
        "current_snapshot_hash": current["snapshot_hash"],
        "changed_files": changed_paths(initial, current),
        "review_verdict": review["verdict"],
        "hard_isolation": hard_isolation,
        "residual_risk": review.get("residual_risk", "none"),
    }
    write_json(ledger / "acceptance.json", acceptance, exclusive=True)
    if args.json:
        print(json.dumps(acceptance, ensure_ascii=True, sort_keys=True))
    else:
        print(f"ACCEPTED: {run['run_id']} ({'hard read-only' if hard_isolation else 'behavioral read-only with residual risk'})")


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--agent-path")
    parser.add_argument("--model-provider")
    parser.add_argument("--sandbox-policy-type")
    parser.add_argument("--permission-profile-type")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize a new run ledger")
    init.add_argument("--repo", required=True)
    init.add_argument("--ledger-root")
    init.add_argument("--run-id", required=True)
    init.add_argument("--owned-file", action="append", default=[])
    init.set_defaults(function=cmd_init)

    worker = subparsers.add_parser("record-worker", help="record observed implementation routing")
    worker.add_argument("--ledger", required=True)
    add_runtime_arguments(worker)
    worker.set_defaults(function=cmd_record_worker)

    verification = subparsers.add_parser("record-verification", help="record a verification command and immutable evidence hash")
    verification.add_argument("--ledger", required=True)
    verification.add_argument("--command", required=True)
    verification.add_argument("--exit-code", required=True, type=int)
    verification.add_argument("--evidence-file", required=True)
    verification.set_defaults(function=cmd_record_verification)

    snapshot = subparsers.add_parser("snapshot", help="capture repository/artifact state")
    snapshot.add_argument("--ledger", required=True)
    snapshot.add_argument("--label", required=True, choices=("before-review", "after-review"))
    snapshot.set_defaults(function=cmd_snapshot)

    review = subparsers.add_parser("record-review", help="record the fresh Sol review")
    review.add_argument("--ledger", required=True)
    add_runtime_arguments(review)
    review.add_argument("--verdict", required=True, choices=("ship", "fix-first", "rethink"))
    review.add_argument("--reason", required=True)
    review.add_argument("--residual-risk", required=True)
    review.set_defaults(function=cmd_record_review)

    accept = subparsers.add_parser("accept", help="fail-closed acceptance gate")
    accept.add_argument("--ledger", required=True)
    accept.add_argument("--allow-behavioral-read-only", action="store_true")
    accept.add_argument("--json", action="store_true")
    accept.set_defaults(function=cmd_accept)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.function(args)
    except BrokenPipeError:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
