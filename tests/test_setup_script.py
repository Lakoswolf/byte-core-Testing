from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import setup_byte_core as setup


class SetupScriptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.args = argparse.Namespace(
            version="0.1.0", core_root=str(self.parent / "core"),
            state_root=str(self.parent / "state"),
            deployment_root=str(self.parent / "deployment"),
            work_parent=str(self.parent), plan_only=False,
        )
        self.calls = []
        self.cli = mock.Mock()
        self.cli.main.side_effect = self.command
        self.build = mock.Mock(return_value=self.parent / "artifact")
        self.launcher_check = mock.patch.object(setup, "check_launcher_readiness", return_value=0)
        self.readiness = self.launcher_check.start()
        self.addCleanup(self.launcher_check.stop)

    def command(self, args, stdout=None):
        self.calls.append(args)
        if args[0] == "plan":
            stdout.write(json.dumps({"plan_id": args[1] + "-review-id"}))
        return 0

    def execute(self, answers=("install-review-id", "init-review-id")):
        with redirect_stdout(io.StringIO()), mock.patch("builtins.input", side_effect=answers):
            return setup.run(self.args, self.cli, self.build)

    def test_both_approvals_precede_apply_and_each_apply_is_verified(self):
        self.assertEqual(self.execute(), 0)
        self.assertEqual([call[0] for call in self.calls],
                         ["check", "plan", "plan", "apply", "verify", "apply", "verify"])
        self.assertEqual(self.calls[3][2], self.calls[4][2])
        self.assertEqual(self.calls[5][2], self.calls[6][2])
        for plan in self.parent.glob("byte-setup-*/*-plan.json"):
            self.assertEqual(plan.stat().st_mode & 0o777, 0o600)

    def test_second_cancellation_applies_neither_plan(self):
        self.assertEqual(self.execute(("install-review-id", "no")), 5)
        self.assertNotIn("apply", [call[0] for call in self.calls])

    def test_eof_cancels(self):
        self.assertEqual(self.execute(EOFError()), 5)
        self.assertNotIn("apply", [call[0] for call in self.calls])

    def test_unsupported_check_prevents_preparation(self):
        self.cli.main.side_effect = None
        self.cli.main.return_value = 3
        self.assertEqual(self.execute(), 3)
        self.build.assert_not_called()
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_plan_only_never_prompts_or_applies(self):
        self.args.plan_only = True
        self.assertEqual(self.execute(()), 0)
        self.assertEqual([call[0] for call in self.calls], ["check", "plan", "plan"])

    def test_launcher_failure_prevents_preparation(self):
        self.readiness.return_value = 3
        self.assertEqual(self.execute(), 3)
        self.build.assert_not_called()
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_launcher_failure_after_review_prevents_both_applies(self):
        self.readiness.side_effect = [0, 3]
        self.assertEqual(self.execute(), 3)
        self.assertNotIn("apply", [call[0] for call in self.calls])
        self.assertEqual(len(list(self.parent.glob("byte-setup-*/*-plan.json"))), 2)

    def test_existing_root_is_preserved(self):
        target = Path(self.args.deployment_root)
        target.mkdir()
        (target / "note.txt").write_text("Fictional operator note")
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual((target / "note.txt").read_text(), "Fictional operator note")
        self.build.assert_not_called()

    def test_overlapping_and_checkout_roots_are_refused(self):
        for target in (self.args.core_root, str(ROOT / "example-setup")):
            with self.subTest(target=target):
                self.args.state_root = target
                with self.assertRaises(ValueError):
                    self.execute()
        self.build.assert_not_called()

    def test_plan_change_during_review_prevents_apply(self):
        def answer(prompt):
            if "init" in prompt:
                next(self.parent.glob("byte-setup-*/install-plan.json")).write_text("{}")
                return "init-review-id"
            return "install-review-id"
        with self.assertRaises(ValueError):
            self.execute(answer)
        self.assertNotIn("apply", [call[0] for call in self.calls])

    def test_symlink_and_git_metadata_targets_are_refused(self):
        linked = self.parent / "linked"
        linked.symlink_to(self.parent / "absent")
        for target in (linked, self.parent / ".git" / "example"):
            with self.subTest(target=target):
                self.args.core_root = str(target)
                with self.assertRaises(ValueError):
                    self.execute()
        self.build.assert_not_called()

    def test_invalid_python_stops_before_importing_core(self):
        with mock.patch.object(sys, "version_info", (3, 9)), mock.patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(setup.main([
                "--version", self.args.version, "--core-root", self.args.core_root,
                "--state-root", self.args.state_root,
                "--deployment-root", self.args.deployment_root,
                "--work-parent", self.args.work_parent,
            ]), 3)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_failed_install_verification_prevents_initialization(self):
        def command(args, stdout=None):
            status = self.command(args, stdout)
            return 6 if args[0] == "verify" else status
        self.cli.main.side_effect = command
        self.assertEqual(self.execute(), 6)
        self.assertEqual([call[0] for call in self.calls],
                         ["check", "plan", "plan", "apply", "verify"])

    @unittest.skipIf(sys.version_info < (3, 11), "Core requires Python 3.11+")
    def test_real_lifecycle_with_fixture_readiness(self):
        sys.path.insert(0, str(ROOT / "src"))
        from byte_core import cli
        from build_release_artifact import build
        self.cli, self.build = cli, build
        report = cli.CheckReport("check", True, ())
        def approve(prompt):
            name = "init" if "init" in prompt else "install"
            plan = next(self.parent.glob(f"byte-setup-*/{name}-plan.json"))
            return json.loads(plan.read_text())["plan_id"]
        with mock.patch.object(cli, "collect_check_report", return_value=report):
            self.assertEqual(self.execute(approve), 0)
        self.assertEqual(len(list(Path(self.args.deployment_root).iterdir())), 5)
        self.assertTrue((Path(self.args.state_root) / "installation.json").is_file())


class LauncherReadinessTests(unittest.TestCase):
    def test_uses_posix_launcher_and_read_only_check(self):
        with mock.patch.object(setup.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(setup.check_launcher_readiness(), 0)
        self.assertEqual(run.call_args.args[0], [str(ROOT / "bin" / "byte"), "check"])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)

    def test_missing_incompatible_or_hanging_launcher_refuses_with_guidance(self):
        for outcome in (mock.Mock(returncode=1), mock.Mock(returncode=3),
                        FileNotFoundError(), PermissionError(),
                        subprocess.TimeoutExpired("byte", 15)):
            with self.subTest(outcome=type(outcome).__name__):
                with mock.patch.object(setup.subprocess, "run") as run:
                    if isinstance(outcome, Exception):
                        run.side_effect = outcome
                    else:
                        run.return_value = outcome
                    with mock.patch("sys.stderr", new=io.StringIO()) as errors:
                        self.assertEqual(setup.check_launcher_readiness(), 3)
                    self.assertIn("python3 on PATH", errors.getvalue())
                    self.assertIn("Git", errors.getvalue())
                    self.assertIn("./bin/byte check", errors.getvalue())
