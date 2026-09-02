#!/usr/bin/env python3
"""Regression tests for the route-aware FLOC*Loom execution ledger."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("ledger.py")


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="floc-loom-ledger-test-")
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "FLOC*Loom Tests")
        (self.repo / "README.md").write_text("baseline\n", encoding="utf-8")
        (self.repo / "other.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "README.md", "other.txt")
        self.git("commit", "-qm", "baseline")
        self.ledger_root = self.root / "runs"
        self.run_id = "11111111-1111-7111-8111-111111111111"
        self.ledger = self.ledger_root / self.run_id
        self.worker_id = "22222222-2222-7222-8222-222222222222"
        self.review_id = "33333333-3333-7333-8333-333333333333"
        self.evidence = self.root / "verification.txt"
        self.evidence.write_text("verification passed\n", encoding="utf-8")
        self.coverage = self.root / "coverage.json"
        self.coverage_schema = self.read_coverage_schema()
        self.coverage_categories = [entry["id"] for entry in self.coverage_schema["categories"]]
        self.coverage_triggers = [entry["id"] for entry in self.coverage_schema["triggers"]]
        self.write_coverage(triggered=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *arguments],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def ledger_cmd(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"ledger command failed: {result.stderr}\nstdout={result.stdout}")
        return result

    def read_coverage_schema(self) -> dict[str, object]:
        result = self.ledger_cmd("coverage-schema", "--json")
        try:
            schema = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"coverage-schema did not emit JSON: {exc}\nstdout={result.stdout}")
        self.assertIsInstance(schema, dict)
        return schema

    def init(self, route: str, owned: str = "README.md") -> None:
        self.ledger_cmd(
            "init",
            "--repo",
            str(self.repo),
            "--ledger-root",
            str(self.ledger_root),
            "--run-id",
            self.run_id,
            "--route",
            route,
            "--owned-file",
            owned,
        )

    def record_worker(self, *, role: str = "floc_loom_luna_implementer") -> None:
        pins = {
            "floc_loom_luna_implementer": ("gpt-5.6-luna", "max"),
            "floc_loom_terra_implementer": ("gpt-5.6-terra", "max"),
        }
        model, effort = pins[role]
        self.ledger_cmd(
            "record-worker",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.worker_id,
            "--role",
            role,
            "--model",
            model,
            "--effort",
            effort,
            "--cwd",
            str(self.repo),
        )

    def record_verification(self, *, exit_code: int = 0, command: str = "test command") -> None:
        self.ledger_cmd(
            "record-verification",
            "--ledger",
            str(self.ledger),
            "--command",
            command,
            "--exit-code",
            str(exit_code),
            "--evidence-file",
            str(self.evidence),
        )

    def snapshot(self, label: str) -> None:
        self.ledger_cmd("snapshot", "--ledger", str(self.ledger), "--label", label)

    def write_coverage(self, *, triggered: bool, safe: bool = True) -> None:
        if triggered:
            coverage = {
                "schema_version": 1,
                "sweep_triggered": True,
                "triggers": [self.coverage_triggers[0]],
                "inspected": self.coverage_categories,
                "exclusions": [],
            }
        else:
            reason = "Not applicable to this change." if safe else "See https://example.invalid/private-token"
            coverage = {
                "schema_version": 1,
                "sweep_triggered": False,
                "triggers": [],
                "inspected": [],
                "exclusions": [{"category": category, "reason": reason} for category in self.coverage_categories],
            }
        self.coverage.write_text(json.dumps(coverage), encoding="utf-8")

    def record_review(self, *, sandbox: str = "read-only", residual_risk: str = "none") -> None:
        self.ledger_cmd(
            "record-review",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.review_id,
            "--role",
            "floc_loom_sol_reviewer",
            "--model",
            "gpt-5.6-sol",
            "--effort",
            "high",
            "--cwd",
            str(self.repo),
            "--sandbox-policy-type",
            sandbox,
            "--permission-profile-type",
            "disabled" if sandbox != "read-only" else "read-only",
            "--verdict",
            "ship",
            "--reason",
            "diff and evidence inspected",
            "--residual-risk",
            residual_risk,
            "--coverage-file",
            str(self.coverage),
        )

    def complete_delegate_packet(self) -> None:
        self.init("delegate")
        self.record_worker()
        self.record_verification()
        self.snapshot("verified-state")

    def complete_audit_packet(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()

    def complete_full_packet(self, *, role: str = "floc_loom_luna_implementer") -> None:
        self.init("full")
        self.record_worker(role=role)
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()

    def test_requires_route_at_initialization(self) -> None:
        result = self.ledger_cmd(
            "init",
            "--repo",
            str(self.repo),
            "--ledger-root",
            str(self.ledger_root),
            "--run-id",
            self.run_id,
            "--owned-file",
            "README.md",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--route", result.stderr)

    def test_accepts_delegate_with_luna_and_verified_state_binding(self) -> None:
        self.complete_delegate_packet()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "delegate"', result.stdout)
        self.assertTrue((self.ledger / "acceptance.json").is_file())

    def test_accepts_audit_with_root_verification_and_review_only(self) -> None:
        self.complete_audit_packet()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "audit"', result.stdout)
        self.assertNotIn('"hard_isolation": null', result.stdout)

    def test_accepts_full_with_terra_worker(self) -> None:
        self.complete_full_packet(role="floc_loom_terra_implementer")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "full"', result.stdout)

    def test_delegate_rejects_terra_worker(self) -> None:
        self.init("delegate")
        result = self.ledger_cmd(
            "record-worker",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.worker_id,
            "--role",
            "floc_loom_terra_implementer",
            "--model",
            "gpt-5.6-terra",
            "--effort",
            "max",
            "--cwd",
            str(self.repo),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Terra requires full", result.stderr)

    def test_delegate_rejects_review_evidence(self) -> None:
        self.init("delegate")
        result = self.ledger_cmd(
            "record-review",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.review_id,
            "--role",
            "floc_loom_sol_reviewer",
            "--model",
            "gpt-5.6-sol",
            "--effort",
            "high",
            "--cwd",
            str(self.repo),
            "--sandbox-policy-type",
            "read-only",
            "--permission-profile-type",
            "read-only",
            "--verdict",
            "ship",
            "--reason",
            "diff and evidence inspected",
            "--residual-risk",
            "none",
            "--coverage-file",
            str(self.coverage),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("delegate route forbids Sol review evidence", result.stderr)

    def test_audit_rejects_worker_evidence(self) -> None:
        self.init("audit")
        result = self.ledger_cmd(
            "record-worker",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.worker_id,
            "--role",
            "floc_loom_luna_implementer",
            "--model",
            "gpt-5.6-luna",
            "--effort",
            "max",
            "--cwd",
            str(self.repo),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("audit route rejects worker evidence", result.stderr)

    def test_delegate_rejects_post_verification_mutation(self) -> None:
        self.complete_delegate_packet()
        (self.repo / "README.md").write_text("changed after verification\n", encoding="utf-8")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository changed after the verified-state", result.stderr)

    def test_rejects_changed_verification_evidence(self) -> None:
        self.complete_delegate_packet()
        self.evidence.write_text("verification evidence changed\n", encoding="utf-8")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verification evidence changed", result.stderr)

    def test_delegate_rejects_missing_verified_state(self) -> None:
        self.init("delegate")
        self.record_worker()
        self.record_verification()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verified-state.json", result.stderr)

    def test_audit_rejects_worker_record_created_outside_cli(self) -> None:
        self.complete_audit_packet()
        worker = {
            "schema_version": 2,
            "thread_id": self.worker_id,
            "agent_role": "floc_loom_luna_implementer",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "cwd": str(self.repo),
        }
        (self.ledger / "workers" / f"{self.worker_id}.json").write_text(json.dumps(worker), encoding="utf-8")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("audit route requires verification and review evidence with no worker evidence", result.stderr)

    def test_full_rejects_missing_review(self) -> None:
        self.init("full")
        self.record_worker()
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("review.json", result.stderr)

    def test_full_rejects_second_worker(self) -> None:
        self.init("full")
        self.record_worker()
        result = self.ledger_cmd(
            "record-worker",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            "44444444-4444-7444-8444-444444444444",
            "--role",
            "floc_loom_terra_implementer",
            "--model",
            "gpt-5.6-terra",
            "--effort",
            "max",
            "--cwd",
            str(self.repo),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one implementation worker", result.stderr)

    def test_audit_rejects_review_mutation(self) -> None:
        self.complete_audit_packet()
        (self.repo / "README.md").write_text("changed after review\n", encoding="utf-8")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository changed after the after-review", result.stderr)

    def test_rejects_out_of_scope_changes(self) -> None:
        self.init("full")
        self.record_worker()
        (self.repo / "other.txt").write_text("out of scope\n", encoding="utf-8")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out-of-scope files changed", result.stderr)

    def test_behavioral_read_only_requires_explicit_opt_in(self) -> None:
        self.init("full")
        self.record_worker()
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review(sandbox="danger-full-access", residual_risk="host broadened reviewer sandbox")
        rejected = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("--allow-behavioral-read-only", rejected.stderr)
        accepted = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--allow-behavioral-read-only")
        self.assertIn("behavioral read-only", accepted.stdout)

    def test_public_coverage_schema_is_deterministic_and_supports_a_review_packet(self) -> None:
        repeated = self.read_coverage_schema()
        self.assertEqual(repeated, self.coverage_schema)
        self.assertEqual(self.coverage_schema["schema_version"], 1)
        self.assertEqual(self.coverage_schema["coverage_schema_version"], 1)
        self.assertEqual(
            self.coverage_schema["semantic_source"],
            "references/role-contracts.md#conditional-security-and-observability-sweep",
        )
        self.assertEqual(len(self.coverage_triggers), len(set(self.coverage_triggers)))
        self.assertEqual(len(self.coverage_categories), len(set(self.coverage_categories)))
        self.assertGreater(len(self.coverage_triggers), 0)
        self.assertGreater(len(self.coverage_categories), 0)

        core = {key: value for key, value in self.coverage_schema.items() if key != "fingerprint"}
        expected_fingerprint = "sha256:" + hashlib.sha256(
            json.dumps(core, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(self.coverage_schema["fingerprint"], expected_fingerprint)

        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()
        accepted = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "audit"', accepted.stdout)

    def test_coverage_schema_and_validator_detect_identifier_drift(self) -> None:
        core = {key: value for key, value in self.coverage_schema.items() if key != "fingerprint"}
        drifted_core = json.loads(json.dumps(core))
        drifted_core["categories"][0]["id"] = "identifier-drift"
        drifted_fingerprint = "sha256:" + hashlib.sha256(
            json.dumps(drifted_core, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertNotEqual(self.coverage_schema["fingerprint"], drifted_fingerprint)

        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.coverage.write_text(
            json.dumps(
                {
                    "schema_version": self.coverage_schema["coverage_schema_version"],
                    "sweep_triggered": True,
                    "triggers": [self.coverage_triggers[0]],
                    "inspected": ["identifier-drift", *self.coverage_categories[1:]],
                    "exclusions": [],
                }
            ),
            encoding="utf-8",
        )
        rejected = self.ledger_cmd(
            "record-review",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.review_id,
            "--role",
            "floc_loom_sol_reviewer",
            "--model",
            "gpt-5.6-sol",
            "--effort",
            "high",
            "--cwd",
            str(self.repo),
            "--sandbox-policy-type",
            "read-only",
            "--permission-profile-type",
            "read-only",
            "--verdict",
            "ship",
            "--reason",
            "diff and evidence inspected",
            "--residual-risk",
            "none",
            "--coverage-file",
            str(self.coverage),
            check=False,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("unknown or duplicate category", rejected.stderr)

    def test_coverage_requires_complete_partition_and_safe_exclusions(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.write_coverage(triggered=False, safe=False)
        result = self.ledger_cmd(
            "record-review",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.review_id,
            "--role",
            "floc_loom_sol_reviewer",
            "--model",
            "gpt-5.6-sol",
            "--effort",
            "high",
            "--cwd",
            str(self.repo),
            "--sandbox-policy-type",
            "read-only",
            "--permission-profile-type",
            "read-only",
            "--verdict",
            "ship",
            "--reason",
            "diff and evidence inspected",
            "--residual-risk",
            "none",
            "--coverage-file",
            str(self.coverage),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive value or payload marker", result.stderr)

    def test_accepts_non_triggered_coverage_with_justified_exclusions(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.write_coverage(triggered=False)
        self.record_review()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "audit"', result.stdout)

    def test_route_escalation_is_monotonic_and_preserves_declaration(self) -> None:
        self.init("delegate")
        self.ledger_cmd(
            "escalate",
            "--ledger",
            str(self.ledger),
            "--to",
            "full",
            "--reason",
            "The node crossed the high-risk integration boundary.",
        )
        downgraded = self.ledger_cmd(
            "escalate",
            "--ledger",
            str(self.ledger),
            "--to",
            "audit",
            "--reason",
            "Attempted downgrade.",
            check=False,
        )
        self.assertNotEqual(downgraded.returncode, 0)
        self.assertIn("must be monotonic", downgraded.stderr)

        self.record_worker(role="floc_loom_terra_implementer")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"declared_route": "delegate"', result.stdout)
        self.assertIn('"route": "full"', result.stdout)

    def test_delegate_cannot_escalate_to_audit_after_worker_evidence(self) -> None:
        self.init("delegate")
        self.record_worker()
        result = self.ledger_cmd(
            "escalate",
            "--ledger",
            str(self.ledger),
            "--to",
            "audit",
            "--reason",
            "Need a fresh review.",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot escalate to audit after worker evidence", result.stderr)

    def test_audit_requires_verification_before_review_boundary(self) -> None:
        self.init("audit")
        result = self.ledger_cmd(
            "snapshot",
            "--ledger",
            str(self.ledger),
            "--label",
            "before-review",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no verification evidence", result.stderr)

    def test_full_requires_worker_before_review_boundary(self) -> None:
        self.init("full")
        self.record_verification()
        result = self.ledger_cmd(
            "snapshot",
            "--ledger",
            str(self.ledger),
            "--label",
            "before-review",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one implementation worker", result.stderr)

    def test_active_review_boundary_rejects_new_verification(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        result = self.ledger_cmd(
            "record-verification",
            "--ledger",
            str(self.ledger),
            "--command",
            "late verification",
            "--exit-code",
            "0",
            "--evidence-file",
            str(self.evidence),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("while a final review boundary is active", result.stderr)

    def test_after_review_rejects_reviewer_mutation_immediately(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        (self.repo / "README.md").write_text("reviewer mutation\n", encoding="utf-8")
        result = self.ledger_cmd(
            "snapshot",
            "--ledger",
            str(self.ledger),
            "--label",
            "after-review",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("read-only boundary failed", result.stderr)

    def test_unaccepted_review_boundary_can_restart_after_one_correction(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")

        (self.repo / "README.md").write_text("bounded correction\n", encoding="utf-8")
        self.record_verification(command="post-fix verification")
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()

        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "audit"', result.stdout)

    def test_failed_verification_history_does_not_poison_later_success(self) -> None:
        self.init("delegate")
        self.record_worker()
        self.record_verification(exit_code=1, command="failing test")
        self.record_verification(command="passing test")
        self.snapshot("verified-state")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"route": "delegate"', result.stdout)

    def test_non_triggered_coverage_rejects_inspected_categories(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        coverage = {
            "schema_version": 1,
            "sweep_triggered": False,
            "triggers": [],
            "inspected": [self.coverage_categories[0]],
            "exclusions": [
                {"category": category, "reason": "Not applicable to this change."}
                for category in self.coverage_categories[1:]
            ],
        }
        self.coverage.write_text(json.dumps(coverage), encoding="utf-8")
        result = self.ledger_cmd(
            "record-review",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.review_id,
            "--role",
            "floc_loom_sol_reviewer",
            "--model",
            "gpt-5.6-sol",
            "--effort",
            "high",
            "--cwd",
            str(self.repo),
            "--sandbox-policy-type",
            "read-only",
            "--permission-profile-type",
            "read-only",
            "--verdict",
            "ship",
            "--reason",
            "diff and evidence inspected",
            "--residual-risk",
            "none",
            "--coverage-file",
            str(self.coverage),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not mark categories as inspected", result.stderr)

    def test_route_cannot_escalate_after_review_boundary_started(self) -> None:
        self.init("audit")
        self.record_verification()
        self.snapshot("before-review")
        result = self.ledger_cmd(
            "escalate",
            "--ledger",
            str(self.ledger),
            "--to",
            "full",
            "--reason",
            "Too late.",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("after a final review boundary has started", result.stderr)

    def test_accepted_run_rejects_additional_evidence(self) -> None:
        self.complete_delegate_packet()
        self.ledger_cmd("accept", "--ledger", str(self.ledger))
        result = self.ledger_cmd(
            "record-verification",
            "--ledger",
            str(self.ledger),
            "--command",
            "late evidence",
            "--exit-code",
            "0",
            "--evidence-file",
            str(self.evidence),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already accepted", result.stderr)

    def test_immutable_route_declaration_tamper_is_rejected(self) -> None:
        self.init("delegate")
        declaration = self.ledger / "route-declaration.json"
        data = json.loads(declaration.read_text(encoding="utf-8"))
        data["route"] = "full"
        declaration.write_text(json.dumps(data), encoding="utf-8")
        result = self.ledger_cmd("record-verification", "--ledger", str(self.ledger), "--command", "test", "--exit-code", "0", "--evidence-file", str(self.evidence), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("immutable route declaration integrity check failed", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
