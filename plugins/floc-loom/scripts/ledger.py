#!/usr/bin/env python3
"""Fail-closed, route-aware execution ledger for FLOC*Loom runs.

The Codex host remains responsible for spawning native agents. This ledger makes the
acceptance evidence for one direct deliverable or graph node explicit and
machine-checkable. It records an immutable route declaration, observed role pins,
verification evidence, review metadata, repository snapshots, and the allowed file
set. ``solo`` is deliberately outside this ledger: it cannot be used to launder a
mutation or auxiliary-agent run through a weaker acceptance gate.
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
from typing import Any, NoReturn


SCHEMA_VERSION = 2
COVERAGE_SCHEMA_VERSION = 1
COVERAGE_DISCOVERY_SCHEMA_VERSION = 1
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ROLE_PINS = {
    "floc_loom_luna_implementer": {"model": "gpt-5.6-luna", "effort": "max"},
    "floc_loom_terra_implementer": {"model": "gpt-5.6-terra", "effort": "max"},
    "floc_loom_sol_reviewer": {"model": "gpt-5.6-sol", "effort": "high"},
}
REVIEW_ROLE = "floc_loom_sol_reviewer"
LUNA_ROLE = "floc_loom_luna_implementer"
TERRA_ROLE = "floc_loom_terra_implementer"
LEDGER_ROUTES = ("delegate", "audit", "full")
ROUTE_RANK = {"delegate": 1, "audit": 2, "full": 3}

# These identifiers intentionally describe review coverage without recording a
# payload, endpoint, prompt, credential, environment value, or configuration value.
# ``coverage-schema --json`` is the public, exact mapping. The adjacent semantic text
# deliberately matches the role-contract source so the shipped verifier can bind the
# machine allowlist to the human review contract without duplicating identifiers there.
COVERAGE_TRIGGER_DEFINITIONS = (
    ("provider-client-io", "provider/client I/O"),
    ("logging", "logging"),
    ("telemetry", "telemetry"),
    ("exception-handling", "exception handling"),
    ("schemas", "schemas"),
    ("serialization", "serialization"),
    ("configuration", "configuration"),
    ("urls", "URLs"),
    ("credentials", "credentials"),
    ("transport-debugging", "transport debugging"),
)
COVERAGE_CATEGORY_DEFINITIONS = (
    ("ingress-parsing-validation", "Ingress, parsing, validation, and serialization."),
    (
        "control-flow-success-exception-fallback-cache-early-return",
        "Success, exception, fallback, cache, and early-return control flow.",
    ),
    (
        "observability-sinks-logs-failure-records-usage-summaries-transport-debug",
        "Application logs, failure records, usage observations, summaries, and transport/debug sinks.",
    ),
    ("configuration-url-metadata", "Configuration-derived endpoint and URL metadata."),
    (
        "sequential-state-safe-default-transitions",
        "Stale state across sequential calls plus safe/default transitions.",
    ),
)
COVERAGE_TRIGGERS = frozenset(identifier for identifier, _ in COVERAGE_TRIGGER_DEFINITIONS)
COVERAGE_CATEGORIES = frozenset(identifier for identifier, _ in COVERAGE_CATEGORY_DEFINITIONS)
SENSITIVE_COVERAGE_RE = re.compile(
    r"(?:https?://|www\.|api[ _-]?key|secret|password|authorization|bearer|"
    r"credential|token|prompt|(?:request|response)[ _-]?body|"
    r"(?:environment|env)[ _-]?(?:value|variable)|"
    r"config(?:uration)?[ _-]?(?:value|secret)|=)",
    re.IGNORECASE,
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coverage_schema_document() -> dict[str, Any]:
    """Return the public, deterministic coverage-ID and artifact contract."""
    core = {
        "schema_version": COVERAGE_DISCOVERY_SCHEMA_VERSION,
        "coverage_schema_version": COVERAGE_SCHEMA_VERSION,
        "semantic_source": "references/role-contracts.md#conditional-security-and-observability-sweep",
        "required_fields": ["schema_version", "sweep_triggered", "triggers", "inspected", "exclusions"],
        "exclusion_required_fields": ["category", "reason"],
        "validation_rules": {
            "triggered_requires_at_least_one_trigger": True,
            "non_triggered_requires_no_triggers": True,
            "categories_require_exact_inspected_or_excluded_partition": True,
            "exclusion_reason_must_be_short_single_line_non_sensitive": True,
        },
        "triggers": [
            {"id": identifier, "semantic_text": semantic_text}
            for identifier, semantic_text in COVERAGE_TRIGGER_DEFINITIONS
        ],
        "categories": [
            {"id": identifier, "semantic_text": semantic_text}
            for identifier, semantic_text in COVERAGE_CATEGORY_DEFINITIONS
        ],
    }
    return {**core, "fingerprint": f"sha256:{sha256_bytes(canonical_json(core))}"}


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


def require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} is required")
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
    if value.get("schema_version") != SCHEMA_VERSION:
        fail(f"snapshot schema is unsupported: {path}")
    core = {key: value[key] for key in ("schema_version", "git_head", "status_sha256", "diff_sha256", "files")}
    if value["snapshot_hash"] != sha256_bytes(canonical_json(core)):
        fail(f"snapshot hash mismatch: {path}")


def load_run(ledger: Path) -> dict[str, Any]:
    ledger = ledger.resolve()
    run_path = ledger / "run.json"
    run = read_json(run_path)
    if run.get("schema_version") != SCHEMA_VERSION:
        fail(f"unsupported ledger schema in {run_path}; create a new route-aware ledger")
    validate_uuid(str(run.get("run_id", "")), "run_id")
    route = run.get("route")
    if route not in LEDGER_ROUTES:
        fail("ledger route declaration is missing or invalid; create a new ledger with --route delegate|audit|full")
    repo = canonical_repo(str(run.get("repo", "")))
    if str(repo) != str(Path(run["repo"]).resolve()):
        fail("ledger repository path changed after initialization")

    declaration_path = ledger / "route-declaration.json"
    declaration = read_json(declaration_path)
    expected_hash = run.get("route_declaration_sha256")
    if not isinstance(expected_hash, str) or expected_hash != sha256_bytes(canonical_json(declaration)):
        fail("immutable route declaration integrity check failed")
    if (
        declaration.get("schema_version") != SCHEMA_VERSION
        or declaration.get("run_id") != run["run_id"]
        or declaration.get("route") != route
        or declaration.get("repo") != run["repo"]
    ):
        fail("immutable route declaration does not match the initialized run")
    return run


def load_artifacts(ledger: Path, directory: str) -> list[dict[str, Any]]:
    folder = ledger / directory
    if not folder.is_dir():
        return []
    artifacts = []
    for path in sorted(folder.glob("*.json")):
        artifacts.append(read_json(path))
    return artifacts


def require_open_run(ledger: Path) -> None:
    if (ledger / "acceptance.json").exists():
        fail("ledger run is already accepted and cannot record additional evidence")


def review_boundary_active(ledger: Path) -> bool:
    return (ledger / "before-review.json").exists() and not (ledger / "after-review.json").exists()


def active_route(ledger: Path, run: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    current = str(run["route"])
    escalations = load_artifacts(ledger, "escalations")
    for index, escalation in enumerate(escalations, start=1):
        if escalation.get("schema_version") != SCHEMA_VERSION:
            fail("route escalation has an unsupported schema")
        if escalation.get("run_id") != run["run_id"]:
            fail("route escalation belongs to a different ledger run")
        if escalation.get("sequence") != index:
            fail("route escalation sequence is invalid")
        if escalation.get("from_route") != current:
            fail("route escalation does not continue from the active route")
        target = escalation.get("to_route")
        if target not in LEDGER_ROUTES or ROUTE_RANK[str(target)] <= ROUTE_RANK[current]:
            fail("route escalation is not monotonic")
        require_nonempty_string(escalation.get("reason"), "route escalation reason")
        current = str(target)
    return current, escalations


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
    if args.route not in LEDGER_ROUTES:
        fail("--route must be delegate, audit, or full; solo is outside this ledger")
    if not args.owned_file:
        fail("at least one --owned-file is required")
    owned = sorted({normalize_owned_file(repo, item) for item in args.owned_file})
    root = Path(args.ledger_root).expanduser().resolve() if args.ledger_root else default_ledger_root()
    run_dir = root / run_id
    if run_dir.exists():
        fail(f"ledger run already exists: {run_dir}")
    initial = make_snapshot(repo)
    declaration = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "repo": str(repo),
        "route": args.route,
        "declared_at": now(),
    }
    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "repo": str(repo),
        "created_at": now(),
        "base_commit": initial["git_head"],
        "owned_files": owned,
        "route": args.route,
        "route_declaration_sha256": sha256_bytes(canonical_json(declaration)),
        "review_policy": {"requires_hard_isolation": True},
    }
    try:
        run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
        write_json(run_dir / "run.json", run, exclusive=True)
        write_json(run_dir / "route-declaration.json", declaration, exclusive=True)
        write_json(run_dir / "initial-state.json", initial, exclusive=True)
        (run_dir / "workers").mkdir(mode=0o700)
        (run_dir / "verifications").mkdir(mode=0o700)
        (run_dir / "escalations").mkdir(mode=0o700)
    except OSError as exc:
        fail(f"could not create ledger run {run_dir}: {exc}")
    print(f"LEDGER INITIALIZED: {run_dir} (route={args.route})")


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
    run = load_run(ledger)
    require_open_run(ledger)
    if review_boundary_active(ledger):
        fail("cannot record worker evidence while a final review boundary is active")
    route, _ = active_route(ledger, run)
    if route == "audit":
        fail("audit route rejects worker evidence; root implementation is the required matrix")
    workers = load_artifacts(ledger, "workers")
    if workers:
        fail("this route-scoped ledger permits exactly one implementation worker")
    require_worker_pin(args.role, args.model, args.effort)
    if route == "delegate" and args.role != LUNA_ROLE:
        fail("delegate route accepts only the bounded Luna implementation lane; Terra requires full")
    record = {"schema_version": SCHEMA_VERSION, **common_runtime_fields(args)}
    write_json(ledger / "workers" / f"{args.thread_id}.json", record, exclusive=True)
    print(f"WORKER RECORDED: {args.thread_id} (route={route})")


def cmd_record_verification(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    require_open_run(ledger)
    if review_boundary_active(ledger):
        fail("cannot record verification evidence while a final review boundary is active")
    command = require_nonempty_string(args.command, "verification command")
    evidence = Path(args.evidence_file).expanduser().resolve()
    if not evidence.is_file():
        fail(f"verification evidence file is unavailable: {evidence}")
    if args.exit_code < 0:
        fail("--exit-code cannot be negative")
    repo = canonical_repo(str(run["repo"]))
    record = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "exit_code": args.exit_code,
        "evidence_file": str(evidence),
        "evidence_sha256": sha256_file(evidence),
        "repository_snapshot_hash": make_snapshot(repo)["snapshot_hash"],
        "recorded_at": now(),
    }
    write_json(ledger / "verifications" / f"{uuid.uuid4()}.json", record, exclusive=True)
    print(f"VERIFICATION RECORDED: {command}")


def cmd_snapshot(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    require_open_run(ledger)
    route, _ = active_route(ledger, run)
    repo = canonical_repo(str(run["repo"]))
    current = make_snapshot(repo)

    if args.label == "verified-state":
        if route != "delegate":
            fail("verified-state snapshots are reserved for delegate route state binding")
        workers = validated_workers(ledger)
        if len(workers) != 1 or workers[0].get("agent_role") != LUNA_ROLE:
            fail("delegate verified-state requires exactly one Luna worker evidence record")
        verifications = validated_verifications(ledger)
        require_verification_binding(verifications, str(current["snapshot_hash"]), "verified-state")
        write_json(ledger / "verified-state.json", current, exclusive=True)
    elif args.label == "before-review":
        if route not in {"audit", "full"}:
            fail("review snapshots require audit or full route")
        if (ledger / "review.json").exists():
            fail("accepted review evidence already exists; the review boundary is closed")
        before_path = ledger / "before-review.json"
        after_path = ledger / "after-review.json"
        if before_path.exists() and not after_path.exists():
            fail("a final review boundary is already active")
        require_review_prerequisites(ledger, route, str(current["snapshot_hash"]))
        if after_path.exists():
            try:
                after_path.unlink()
            except OSError as exc:
                fail(f"cannot clear the unaccepted after-review snapshot: {exc}")
        write_json(before_path, current)
    elif args.label == "after-review":
        if route not in {"audit", "full"}:
            fail("review snapshots require audit or full route")
        if (ledger / "review.json").exists():
            fail("accepted review evidence already exists; the review boundary is closed")
        before_path = ledger / "before-review.json"
        after_path = ledger / "after-review.json"
        if after_path.exists():
            fail("after-review snapshot already exists for the active boundary")
        before = read_json(before_path)
        validate_snapshot(before, before_path)
        if current["snapshot_hash"] != before["snapshot_hash"]:
            fail("review changed repository/artifact state; read-only boundary failed")
        write_json(after_path, current, exclusive=True)
    else:
        fail("snapshot label must be verified-state, before-review, or after-review")

    print(f"SNAPSHOT RECORDED: {args.label}")


def require_safe_coverage_reason(value: Any) -> str:
    reason = require_nonempty_string(value, "coverage exclusion reason")
    if len(reason) > 240 or any(character in reason for character in "\r\n\t"):
        fail("coverage exclusion reason must be a short, single-line non-sensitive justification")
    if SENSITIVE_COVERAGE_RE.search(reason):
        fail("coverage exclusion reason appears to contain a sensitive value or payload marker")
    return reason


def validate_coverage(value: dict[str, Any]) -> None:
    required = {"schema_version", "sweep_triggered", "triggers", "inspected", "exclusions"}
    if set(value) != required:
        fail("coverage must contain exactly schema_version, sweep_triggered, triggers, inspected, and exclusions")
    if value.get("schema_version") != COVERAGE_SCHEMA_VERSION:
        fail("coverage schema version is unsupported")
    triggered = value.get("sweep_triggered")
    if not isinstance(triggered, bool):
        fail("coverage sweep_triggered must be a boolean")

    triggers = value.get("triggers")
    if not isinstance(triggers, list) or any(not isinstance(item, str) for item in triggers):
        fail("coverage triggers must be a list of identifiers")
    if len(set(triggers)) != len(triggers) or any(item not in COVERAGE_TRIGGERS for item in triggers):
        fail("coverage triggers contain an unknown or duplicate identifier")
    if triggered and not triggers:
        fail("triggered coverage must name at least one trigger")
    if not triggered and triggers:
        fail("non-triggered coverage must not name triggers")

    inspected = value.get("inspected")
    if not isinstance(inspected, list) or any(not isinstance(item, str) for item in inspected):
        fail("coverage inspected must be a list of category identifiers")
    if len(set(inspected)) != len(inspected) or any(item not in COVERAGE_CATEGORIES for item in inspected):
        fail("coverage inspected contains an unknown or duplicate category")
    if not triggered and inspected:
        fail("non-triggered coverage must not mark categories as inspected")

    exclusions = value.get("exclusions")
    if not isinstance(exclusions, list):
        fail("coverage exclusions must be a list")
    excluded_categories: set[str] = set()
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or set(exclusion) != {"category", "reason"}:
            fail("each coverage exclusion must contain exactly category and reason")
        category = exclusion.get("category")
        if not isinstance(category, str) or category not in COVERAGE_CATEGORIES:
            fail("coverage exclusion contains an unknown category")
        if category in excluded_categories:
            fail("coverage exclusions contain a duplicate category")
        excluded_categories.add(category)
        require_safe_coverage_reason(exclusion.get("reason"))

    inspected_categories = set(inspected)
    if inspected_categories & excluded_categories:
        fail("coverage categories cannot be both inspected and excluded")
    if inspected_categories | excluded_categories != COVERAGE_CATEGORIES:
        fail("coverage must account for every review category by inspection or justified exclusion")


def read_coverage(path: Path) -> dict[str, Any]:
    coverage = read_json(path)
    validate_coverage(coverage)
    return coverage


def cmd_coverage_schema(args: argparse.Namespace) -> None:
    del args
    print(json.dumps(coverage_schema_document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def cmd_record_review(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    require_open_run(ledger)
    route, _ = active_route(ledger, run)
    if route not in {"audit", "full"}:
        fail("delegate route forbids Sol review evidence; its acceptance uses verified-state binding")
    if args.verdict != "ship":
        fail("record-review persists only a final ship verdict; handle fix-first or rethink before persistence")
    require_review_pin(args.role, args.model, args.effort)
    runtime = common_runtime_fields(args)
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
    if before["snapshot_hash"] != after["snapshot_hash"]:
        fail("review changed repository/artifact state; read-only boundary failed")
    require_review_prerequisites(ledger, route, str(before["snapshot_hash"]))
    coverage_path = Path(args.coverage_file).expanduser().resolve()
    if not coverage_path.is_file():
        fail(f"review coverage file is unavailable: {coverage_path}")
    coverage = read_coverage(coverage_path)
    record = {
        "schema_version": SCHEMA_VERSION,
        **runtime,
        "route": route,
        "verdict": args.verdict,
        "reason": args.reason,
        "residual_risk": args.residual_risk,
        "coverage": coverage,
        "coverage_sha256": sha256_bytes(canonical_json(coverage)),
        "before_snapshot_hash": before["snapshot_hash"],
        "after_snapshot_hash": after["snapshot_hash"],
    }
    write_json(ledger / "review.json", record, exclusive=True)
    print(f"REVIEW RECORDED: {args.verdict} (route={route})")


def cmd_escalate(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    require_open_run(ledger)
    if (ledger / "before-review.json").exists():
        fail("cannot escalate after a final review boundary has started")
    current, escalations = active_route(ledger, run)
    target = args.to_route
    if target not in LEDGER_ROUTES or ROUTE_RANK[target] <= ROUTE_RANK[current]:
        fail(f"route escalation must be monotonic from {current} to a stronger route")
    workers = load_artifacts(ledger, "workers")
    if target == "audit" and workers:
        fail("cannot escalate to audit after worker evidence; escalate to full or create a new audit ledger")
    reason = require_nonempty_string(args.reason, "route escalation reason")
    sequence = len(escalations) + 1
    record = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run["run_id"],
        "sequence": sequence,
        "from_route": current,
        "to_route": target,
        "reason": reason,
        "escalated_at": now(),
    }
    write_json(ledger / "escalations" / f"{sequence:04d}.json", record, exclusive=True)
    print(f"ROUTE ESCALATED: {current} -> {target}")


def changed_paths(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_files = before.get("files", {})
    after_files = after.get("files", {})
    paths = set(before_files) | set(after_files)
    return sorted(path for path in paths if before_files.get(path) != after_files.get(path))


def validated_workers(ledger: Path) -> list[dict[str, Any]]:
    workers = load_artifacts(ledger, "workers")
    worker_ids: set[str] = set()
    for worker in workers:
        if worker.get("schema_version") != SCHEMA_VERSION:
            fail("worker evidence has an unsupported schema")
        thread_id = validate_uuid(str(worker.get("thread_id", "")), "worker thread_id")
        if thread_id in worker_ids:
            fail(f"duplicate worker thread id: {thread_id}")
        worker_ids.add(thread_id)
        require_worker_pin(str(worker.get("agent_role", "")), str(worker.get("model", "")), str(worker.get("effort", "")))
        if not worker.get("cwd"):
            fail(f"worker evidence is missing cwd: {thread_id}")
    return workers


def validated_verifications(ledger: Path) -> list[dict[str, Any]]:
    verifications = load_artifacts(ledger, "verifications")
    if not verifications:
        fail("no verification evidence was recorded")
    for verification in verifications:
        if verification.get("schema_version") != SCHEMA_VERSION:
            fail("verification evidence has an unsupported schema")
        exit_code = verification.get("exit_code")
        if not isinstance(exit_code, int) or exit_code < 0:
            fail(f"verification has an invalid exit code: {verification.get('command', '<unknown>')}")
        require_nonempty_string(verification.get("command"), "verification command")
        evidence = Path(str(verification.get("evidence_file", "")))
        if not evidence.is_file():
            fail(f"verification evidence file disappeared: {evidence}")
        if sha256_file(evidence) != verification.get("evidence_sha256"):
            fail(f"verification evidence changed: {evidence}")
        snapshot_hash = verification.get("repository_snapshot_hash")
        if not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
            fail("verification evidence is missing its repository-state binding")
    return verifications


def require_verification_binding(verifications: list[dict[str, Any]], snapshot_hash: str, label: str) -> None:
    if not any(
        verification.get("exit_code") == 0
        and verification.get("repository_snapshot_hash") == snapshot_hash
        for verification in verifications
    ):
        fail(f"no successful verification is bound to the exact {label} repository state")


def require_review_prerequisites(ledger: Path, route: str, snapshot_hash: str) -> None:
    workers = validated_workers(ledger)
    if route == "audit" and workers:
        fail("audit review requires no worker evidence")
    if route == "full" and len(workers) != 1:
        fail("full review requires exactly one implementation worker evidence record")
    verifications = validated_verifications(ledger)
    require_verification_binding(verifications, snapshot_hash, "before-review")


def validated_review(
    ledger: Path,
    before: dict[str, Any],
    after: dict[str, Any],
    expected_route: str,
) -> dict[str, Any]:
    review_path = ledger / "review.json"
    review = read_json(review_path)
    if review.get("schema_version") != SCHEMA_VERSION:
        fail("review evidence has an unsupported schema")
    require_review_pin(str(review.get("agent_role", "")), str(review.get("model", "")), str(review.get("effort", "")))
    validate_uuid(str(review.get("thread_id", "")), "review thread_id")
    if not review.get("cwd"):
        fail("review evidence is missing cwd")
    if not review.get("reason"):
        fail("review evidence is missing reason")
    if not review.get("residual_risk"):
        fail("review evidence is missing residual risk")
    if review.get("route") != expected_route:
        fail("review evidence was recorded for a different active route")
    if review.get("verdict") != "ship":
        fail(f"final Sol review is not ship: {review.get('verdict')}")
    if not review.get("permission_profile_type"):
        fail("review evidence is missing permission profile type")
    if not review.get("sandbox_policy_type"):
        fail("review evidence is missing sandbox policy type")
    if review.get("before_snapshot_hash") != before["snapshot_hash"] or review.get("after_snapshot_hash") != after["snapshot_hash"]:
        fail("review does not reference the recorded before/after snapshots")
    coverage = review.get("coverage")
    if not isinstance(coverage, dict):
        fail("review evidence is missing structured coverage")
    validate_coverage(coverage)
    if review.get("coverage_sha256") != sha256_bytes(canonical_json(coverage)):
        fail("review coverage integrity check failed")
    return review


def check_scope(run: dict[str, Any], initial: dict[str, Any], current: dict[str, Any]) -> None:
    owned_files = set(run.get("owned_files", []))
    out_of_scope = [
        path
        for path in changed_paths(initial, current)
        if not any(path == owned or path.startswith(f"{owned}/") for owned in owned_files)
    ]
    if out_of_scope:
        fail("out-of-scope files changed: " + ", ".join(out_of_scope))


def cmd_accept(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser().resolve()
    run = load_run(ledger)
    require_open_run(ledger)
    route, escalations = active_route(ledger, run)
    initial_path = ledger / "initial-state.json"
    initial = read_json(initial_path)
    validate_snapshot(initial, initial_path)
    workers = validated_workers(ledger)
    verifications = validated_verifications(ledger)
    repo = canonical_repo(str(run["repo"]))

    acceptance: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run["run_id"],
        "declared_route": run["route"],
        "route": route,
        "route_escalations": len(escalations),
        "accepted_at": now(),
    }

    if route == "delegate":
        if args.allow_behavioral_read_only:
            fail("--allow-behavioral-read-only applies only to audit or full Sol review")
        if len(workers) != 1:
            fail("delegate route requires exactly one Luna worker evidence record")
        if workers[0].get("agent_role") != LUNA_ROLE:
            fail("delegate route requires Luna worker evidence; Terra is accepted only for full")
        if (ledger / "review.json").exists():
            fail("delegate route must not contain Sol review evidence")
        verified_path = ledger / "verified-state.json"
        verified = read_json(verified_path)
        validate_snapshot(verified, verified_path)
        require_verification_binding(verifications, str(verified["snapshot_hash"]), "verified-state")
        current = make_snapshot(repo)
        if current["snapshot_hash"] != verified["snapshot_hash"]:
            fail("repository changed after the verified-state snapshot")
        check_scope(run, initial, current)
        acceptance.update(
            {
                "current_snapshot_hash": current["snapshot_hash"],
                "changed_files": changed_paths(initial, current),
                "verification_state_binding": verified["snapshot_hash"],
                "review_verdict": None,
                "hard_isolation": None,
                "residual_risk": None,
            }
        )
        mode = "delegate verified-state binding"
    else:
        expected_workers = 0 if route == "audit" else 1
        if len(workers) != expected_workers:
            if route == "audit":
                fail("audit route requires verification and review evidence with no worker evidence")
            fail("full route requires exactly one Luna or Terra worker evidence record")
        before_path = ledger / "before-review.json"
        after_path = ledger / "after-review.json"
        before = read_json(before_path)
        after = read_json(after_path)
        validate_snapshot(before, before_path)
        validate_snapshot(after, after_path)
        require_verification_binding(verifications, str(before["snapshot_hash"]), "before-review")
        review = validated_review(ledger, before, after, route)
        if before["snapshot_hash"] != after["snapshot_hash"]:
            fail("review changed repository/artifact state; read-only acceptance failed")

        hard_isolation = review["sandbox_policy_type"] == "read-only"
        if not hard_isolation:
            if not args.allow_behavioral_read_only:
                fail("review sandbox was not observed as read-only; pass --allow-behavioral-read-only only when hard isolation is not required")
            if str(review.get("residual_risk", "")).strip().lower() in {"", "none", "none."}:
                fail("behavioral read-only acceptance requires explicit residual-risk reporting")

        current = make_snapshot(repo)
        if current["snapshot_hash"] != after["snapshot_hash"]:
            fail("repository changed after the after-review snapshot")
        check_scope(run, initial, current)
        acceptance.update(
            {
                "current_snapshot_hash": current["snapshot_hash"],
                "changed_files": changed_paths(initial, current),
                "review_verdict": review["verdict"],
                "hard_isolation": hard_isolation,
                "residual_risk": review.get("residual_risk", "none"),
                "coverage_sha256": review["coverage_sha256"],
            }
        )
        mode = "hard read-only" if hard_isolation else "behavioral read-only with residual risk"

    write_json(ledger / "acceptance.json", acceptance, exclusive=True)
    if args.json:
        print(json.dumps(acceptance, ensure_ascii=True, sort_keys=True))
    else:
        print(f"ACCEPTED: {run['run_id']} ({mode})")


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

    coverage_schema = subparsers.add_parser(
        "coverage-schema",
        help="emit the public exact coverage identifier and artifact schema",
    )
    coverage_schema.add_argument(
        "--json",
        action="store_true",
        help="explicitly request the deterministic JSON document (the default output)",
    )
    coverage_schema.set_defaults(function=cmd_coverage_schema)

    init = subparsers.add_parser("init", help="initialize a new route-scoped run ledger")
    init.add_argument("--repo", required=True)
    init.add_argument("--ledger-root")
    init.add_argument("--run-id", required=True)
    init.add_argument("--route", required=True, choices=LEDGER_ROUTES)
    init.add_argument("--owned-file", action="append", default=[])
    init.set_defaults(function=cmd_init)

    escalate = subparsers.add_parser("escalate", help="monotonically escalate an initialized route")
    escalate.add_argument("--ledger", required=True)
    escalate.add_argument("--to", dest="to_route", required=True, choices=LEDGER_ROUTES)
    escalate.add_argument("--reason", required=True)
    escalate.set_defaults(function=cmd_escalate)

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
    snapshot.add_argument("--label", required=True, choices=("verified-state", "before-review", "after-review"))
    snapshot.set_defaults(function=cmd_snapshot)

    review = subparsers.add_parser("record-review", help="record the fresh Sol review")
    review.add_argument("--ledger", required=True)
    add_runtime_arguments(review)
    review.add_argument("--verdict", required=True, choices=("ship",))
    review.add_argument("--reason", required=True)
    review.add_argument("--residual-risk", required=True)
    review.add_argument("--coverage-file", required=True)
    review.set_defaults(function=cmd_record_review)

    accept = subparsers.add_parser("accept", help="fail-closed route-aware acceptance gate")
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
