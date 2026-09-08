from __future__ import annotations

import argparse
import copy
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byte_core import helper_setup, setup_cli  # noqa: E402
from byte_core.inventory_io import InventoryError, encode  # noqa: E402


class HelperSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / "prepared.toml"
        self.target = self.root / "helpers.toml"
        self.source.write_bytes(b"# Preserve this fictional user's comment.\r\nschema_version = 1\r\n")

    def plan(self, **kwargs):
        return helper_setup.build_plan(str(self.source), str(self.target), **kwargs)

    def test_offline_plan_preserves_input_and_reports_unknowns(self):
        before = list(self.root.iterdir())
        with patch.object(subprocess, "Popen", side_effect=AssertionError("no processes")), \
                patch.object(socket, "socket", side_effect=AssertionError("no network")):
            plan = self.plan()
            self.assertEqual(plan, self.plan())
        self.assertEqual(before, list(self.root.iterdir()))
        self.assertTrue(plan["prerequisites"]["ready"])
        self.assertEqual({item["status"] for item in plan["prerequisites"]["checks"]}, {"unconfigured"})
        self.assertNotIn("fictional user's comment", encode(plan).decode())

    def test_apply_preserves_exact_bytes_and_mode_and_never_overwrites(self):
        plan = self.plan()
        with patch.object(subprocess, "Popen", side_effect=AssertionError("no processes")):
            result = helper_setup.apply(plan, plan["id"])
        self.assertEqual("settings_saved", result["code"])
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertEqual(0o600, self.target.stat().st_mode & 0o777)
        self.assertEqual("verified", helper_setup.verify(plan)["code"])
        with self.assertRaises(InventoryError):
            helper_setup.apply(plan, plan["id"])
        self.assertEqual([], list(self.root.glob(".byte-setup-*")))
        self.source.unlink()
        self.assertEqual("verified", helper_setup.verify(plan)["code"])

    def test_approval_tampering_and_stale_source_refused(self):
        plan = self.plan()
        with self.assertRaisesRegex(helper_setup.SetupError, "not_approved"):
            helper_setup.apply(plan, "wrong")
        tampered = copy.deepcopy(plan)
        tampered["output"] = str(self.root / "another.toml")
        with self.assertRaises(InventoryError):
            helper_setup.apply(tampered, plan["id"])
        self.source.write_text("schema_version = 1\n# Changed\n")
        with self.assertRaisesRegex(helper_setup.SetupError, "plan_stale"):
            helper_setup.apply(plan, plan["id"])
        self.assertFalse(self.target.exists())

    def test_validation_uses_captured_bytes_despite_aba_source_changes(self):
        invalid = b"schema_version = 999\n"
        valid = b"schema_version = 1\n"
        with patch.object(helper_setup, "read_bytes", side_effect=[invalid, valid, invalid]) as reader, \
                patch.object(helper_setup.helpers_config, "read_bytes", reader):
            with self.assertRaisesRegex(helper_setup.helpers_config.HelperConfigError, "schema_version"):
                self.plan()
        self.assertEqual(1, reader.call_count)
        self.assertFalse(self.target.exists())

    def test_parse_errors_do_not_include_selected_content(self):
        for data in (b"fictional_sensitive_marker = [", b"\xff"):
            with self.subTest(data=data):
                self.source.write_bytes(data)
                with self.assertRaisesRegex(helper_setup.helpers_config.HelperConfigError,
                                            "^cannot parse helpers config: use valid UTF-8 TOML$"):
                    helper_setup.check(str(self.source))

    def test_existing_and_symlink_targets_and_core_output_refused(self):
        self.target.write_text("preserve")
        with self.assertRaises(InventoryError):
            self.plan()
        self.assertEqual("preserve", self.target.read_text())
        self.target.unlink()
        self.target.symlink_to(self.root / "missing")
        with self.assertRaises(InventoryError):
            self.plan()
        with self.assertRaisesRegex(InventoryError, "output_in_repository"):
            helper_setup.build_plan(str(self.source), str(ROOT / "fictional-setup.toml"))
        self.source.unlink()
        self.source.symlink_to(ROOT / "templates" / "helpers.toml")
        with self.assertRaises(InventoryError):
            helper_setup.check(str(self.source))

    def test_missing_selected_prerequisites_are_actionable(self):
        self.source.write_text('schema_version = 1\n[shell]\ndevelopment_directory = "' + str(self.root / "missing") + '"\n')
        report = helper_setup.check(str(self.source))
        self.assertFalse(report["ready"])
        self.assertEqual("shell.development_directory", report["checks"][0]["setting"])
        with self.assertRaisesRegex(helper_setup.SetupError, "prerequisites_missing"):
            self.plan()
        self.assertFalse(self.target.exists())

    def test_application_modes_and_path_lookup_do_not_launch(self):
        self.source.write_text('schema_version = 1\n[assistant]\nexecutable = "fictional-app"\nnew_args = []\n')
        with patch.object(helper_setup.shutil, "which", return_value="/fictional/bin/app") as lookup:
            plan = self.plan()
        lookup.assert_called_once_with("fictional-app")
        checks = {item["setting"]: item for item in plan["prerequisites"]["checks"]}
        self.assertEqual("unconfigured", checks["assistant.resume_args"]["status"])
        with patch.object(helper_setup.shutil, "which", return_value=None):
            with self.assertRaisesRegex(helper_setup.SetupError, "prerequisites_missing"):
                helper_setup.apply(plan, plan["id"])
        self.source.write_text('schema_version = 1\n[assistant]\nnew_args = []\n')
        self.assertFalse(helper_setup.check(str(self.source))["ready"])

    def test_profile_is_not_read_or_changed_by_advisory_shell_selection(self):
        asset = self.root / "byte-shell.sh"
        asset.write_text("# fictional shell asset\n")
        profile = self.root / ".bashrc"
        profile.write_text("# fictional profile\n")
        plan = self.plan(home_root=str(self.root), shell="bash", shell_script=str(asset))
        profile.write_text("# independent edit after setup planning\n")
        helper_setup.apply(plan, plan["id"])
        self.assertEqual("# independent edit after setup planning\n", profile.read_text())
        command = next(step for step in plan["next_steps"] if step["action"] == "shell_plan")
        self.assertEqual(["byte", "shell", "plan"], command["argv"][:3])
        self.assertFalse((self.root / ".byte-backups").exists())

    def test_incomplete_shell_selection_and_bash_highlighting_refused(self):
        with self.assertRaisesRegex(helper_setup.SetupError, "options_incomplete"):
            self.plan(shell="bash")
        asset = self.root / "asset.sh"
        asset.write_text("# fictional code\n")
        self.source.write_text('schema_version = 1\n[shell]\nhighlighting = true\nhighlighting_file = "' + str(asset) + '"\n')
        with self.assertRaisesRegex(helper_setup.SetupError, "requires_zsh"):
            self.plan(home_root=str(self.root), shell="bash", shell_script=str(asset))

    def test_changed_directory_identity_refused(self):
        directory = self.root / "output"
        directory.mkdir()
        self.target = directory / "helpers.toml"
        plan = self.plan()
        directory.rename(self.root / "old-output")
        directory.mkdir()
        with self.assertRaisesRegex(helper_setup.SetupError, "plan_stale"):
            helper_setup.apply(plan, plan["id"])
        self.assertFalse(self.target.exists())

    def test_existing_target_race_preserves_competing_file(self):
        plan = self.plan()
        original = os.link

        def competing_link(src, dst, **kwargs):
            self.target.write_text("independent writer")
            return original(src, dst, **kwargs)

        with patch.object(helper_setup.os, "link", side_effect=competing_link):
            with self.assertRaisesRegex(helper_setup.SetupError, "target_exists"):
                helper_setup.apply(plan, plan["id"])
        self.assertEqual("independent writer", self.target.read_text())
        self.assertEqual([], list(self.root.glob(".byte-setup-*")))

    def test_verification_detects_content_and_permission_drift(self):
        plan = self.plan()
        helper_setup.apply(plan, plan["id"])
        self.target.chmod(0o644)
        with self.assertRaisesRegex(helper_setup.SetupError, "verification_failed"):
            helper_setup.verify(plan)
        self.target.chmod(0o600)
        self.target.write_text("schema_version = 1\n# Edited\n")
        with self.assertRaisesRegex(helper_setup.SetupError, "verification_failed"):
            helper_setup.verify(plan)

    def test_verification_checks_the_directory_descriptor_used_for_read(self):
        directory = self.root / "output"
        directory.mkdir()
        self.target = directory / "helpers.toml"
        plan = self.plan()
        helper_setup.apply(plan, plan["id"])
        directory.rename(self.root / "old-output")
        directory.mkdir()
        self.target.write_bytes(self.source.read_bytes())
        self.target.chmod(0o600)
        # Model an earlier directory identity observation, before replacement.
        # Identical file bytes in the newly opened directory must not suffice.
        with patch.object(helper_setup, "_directory_identity", return_value=plan["output_parent"]):
            with self.assertRaisesRegex(helper_setup.SetupError, "verification_failed"):
                helper_setup.verify(plan)

    def test_verify_missing_target_has_sanitized_verification_exit(self):
        plan = self.plan()
        plan_file = self.root / "plan.json"
        plan_file.write_bytes(encode(plan))
        parser = argparse.ArgumentParser()
        setup_cli.add_parser(parser.add_subparsers(dest="command", required=True))
        args = parser.parse_args(["setup", "verify", "--plan", str(plan_file)])
        output, errors = io.StringIO(), io.StringIO()
        self.assertEqual(6, setup_cli.run(args, output, errors))
        self.assertEqual("", output.getvalue())
        self.assertEqual("byte: setup_verification_failed\n", errors.getvalue())

    def test_cli_check_and_plan_output(self):
        parser = argparse.ArgumentParser()
        setup_cli.add_parser(parser.add_subparsers(dest="command", required=True))
        output, errors = io.StringIO(), io.StringIO()
        args = parser.parse_args(["setup", "check", "--settings", str(self.source)])
        self.assertEqual(0, setup_cli.run(args, output, errors))
        self.assertIn('"ready": true', output.getvalue())
        self.assertEqual("", errors.getvalue())
        args = parser.parse_args(["setup", "plan", "--settings", str(self.source), "--output", str(self.target)])
        output = io.StringIO()
        self.assertEqual(0, setup_cli.run(args, output, errors))
        self.assertIn('"kind": "helper_setup_plan"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
