#!/usr/bin/env python3
"""Regression tests for ledger.py using disposable Git repositories."""

from __future__ import annotations

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

    def init(self, owned: str = "README.md") -> None:
        self.ledger_cmd(
            "init",
            "--repo",
            str(self.repo),
            "--ledger-root",
            str(self.ledger_root),
            "--run-id",
            self.run_id,
            "--owned-file",
            owned,
        )

    def record_worker(self) -> None:
        self.ledger_cmd(
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
        )

    def record_verification(self) -> None:
        self.ledger_cmd(
            "record-verification",
            "--ledger",
            str(self.ledger),
            "--command",
            "test command",
            "--exit-code",
            "0",
            "--evidence-file",
            str(self.evidence),
        )

    def snapshot(self, label: str) -> None:
        self.ledger_cmd("snapshot", "--ledger", str(self.ledger), "--label", label)

    def record_review(self, sandbox: str = "read-only", residual_risk: str = "none") -> None:
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
        )

    def complete_review_packet(self) -> None:
        self.init()
        self.record_worker()
        self.record_verification()
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()

    def test_accepts_complete_hard_isolated_run(self) -> None:
        self.complete_review_packet()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), "--json")
        self.assertIn('"hard_isolation": true', result.stdout)
        self.assertTrue((self.ledger / "acceptance.json").is_file())

    def test_rejects_wrong_worker_pin(self) -> None:
        self.init()
        result = self.ledger_cmd(
            "record-worker",
            "--ledger",
            str(self.ledger),
            "--thread-id",
            self.worker_id,
            "--role",
            "floc_loom_luna_implementer",
            "--model",
            "gpt-5.6-sol",
            "--effort",
            "high",
            "--cwd",
            str(self.repo),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("role pin mismatch", result.stderr)

    def test_rejects_review_mutation(self) -> None:
        self.complete_review_packet()
        (self.repo / "README.md").write_text("changed after review\n", encoding="utf-8")
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository changed after", result.stderr)

    def test_rejects_out_of_scope_changes(self) -> None:
        self.init()
        self.record_worker()
        self.record_verification()
        (self.repo / "other.txt").write_text("out of scope\n", encoding="utf-8")
        self.snapshot("before-review")
        self.snapshot("after-review")
        self.record_review()
        result = self.ledger_cmd("accept", "--ledger", str(self.ledger), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out-of-scope files changed", result.stderr)

    def test_behavioral_read_only_requires_explicit_opt_in(self) -> None:
        self.init()
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
