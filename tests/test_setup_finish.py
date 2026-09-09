from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import setup_byte_core as setup
from build_release_artifact import build
from byte_core import cli


class FinishSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "fictional home"
        self.home.mkdir()
        self.profile = self.home / ".bashrc"
        self.original = b"# Fictional user profile\nexport FICTIONAL_PRESERVED=yes\n"
        self.profile.write_bytes(self.original)
        self.profile.chmod(0o640)
        self.readiness = mock.patch.object(cli, "collect_check_report", return_value=cli.CheckReport("check", True, ()))
        self.readiness.start()
        self.addCleanup(self.readiness.stop)
        artifact = build("0.1.0", self.root / "artifact")
        output = io.StringIO()
        self.assertEqual(cli.main(["plan", "install", "--artifact-root", str(artifact),
                                  "--core-root", str(self.root / "core"), "--state-root", str(self.root / "state"),
                                  "--core-version", "0.1.0"], stdout=output), 0)
        self.plan = self.root / "install-plan.json"
        self.plan.write_text(output.getvalue())
        self.assertEqual(cli.main(["apply", "--plan", str(self.plan)], stdout=io.StringIO()), 0)
        self.release = self.root / "core/releases/0.1.0"
        self.helpers = self.root / "chosen helpers.toml"
        self.wrapper = self.root / "chosen session.sh"

    def execute(self, answers, **kwargs):
        values = iter(answers)
        def answer(prompt):
            value = next(values)
            if value in {"APPROVE_HELPERS", "APPROVE_SHELL"}:
                name = "helpers" if value == "APPROVE_HELPERS" else "shell"
                plan = next(self.root.glob(f"byte-config-*/{name}-plan.json"))
                data = json.loads(plan.read_text())
                return data["id" if name == "helpers" else "plan_id"]
            if isinstance(value, Exception):
                raise value
            return value
        with mock.patch("builtins.input", side_effect=answer), redirect_stdout(io.StringIO()):
            return setup.finish_setup(str(self.plan), cli, **kwargs)

    def helper_answers(self, approval=True):
        values = ["y", "", "y", "n", "n", "n", "y", "n", "n", str(self.helpers)]
        if approval:
            values.append("APPROVE_HELPERS")
        return values

    def shell_answers(self, approval=True):
        values = ["y", "y", str(self.home), str(self.wrapper), "y"]
        if approval:
            values.append("APPROVE_SHELL")
        return values

    def test_declining_finish_leaves_profile_and_settings_unchanged(self):
        self.assertEqual(self.execute(["no"]), 0)
        self.assertEqual(self.profile.read_bytes(), self.original)
        self.assertFalse(self.helpers.exists())
        self.assertFalse(list(self.root.glob("byte-config-*")))

    def test_helpers_and_bash_profile_round_trip(self):
        self.assertEqual(self.execute(self.helper_answers() + self.shell_answers()), 0)
        self.assertEqual(self.helpers.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.wrapper.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.profile.read_bytes().startswith(self.original))
        self.assertEqual(self.profile.stat().st_mode & 0o777, 0o640)
        backups = list((self.home / ".byte-backups").iterdir())
        self.assertTrue(any(path.read_bytes() == self.original for path in backups))
        self.assertEqual(cli.main(["setup", "check", "--settings", str(self.helpers)], stdout=io.StringIO()), 0)
        result = subprocess.run(["bash", "--noprofile", "--norc", "-c",
                                 '. "$1"; . "$1"; command -v byte; byte check --format json; byte_status',
                                 "fixture", str(self.wrapper)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], str(self.release / "bin/byte"))
        self.assertIn('"supported": true', result.stdout)
        self.assertIn("Byte shell integration is active", result.stdout)

    def test_plan_only_leaves_helper_target_and_profile_unchanged(self):
        self.assertEqual(self.execute(self.helper_answers(False) + self.shell_answers(False), plan_only=True), 0)
        self.assertFalse(self.helpers.exists())
        self.assertEqual(self.profile.read_bytes(), self.original)
        self.assertFalse((self.home / ".byte-backups").exists())
        self.assertTrue(self.wrapper.is_file())
        self.assertEqual(len(list(self.root.glob("byte-config-*/*-plan.json"))), 2)

    def test_wrong_helper_approval_does_not_publish_settings(self):
        with self.assertRaises(setup.SetupCancelled):
            self.execute(self.helper_answers(False) + ["yes"])
        self.assertFalse(self.helpers.exists())
        self.assertEqual(self.profile.read_bytes(), self.original)

    def test_cancelled_profile_preserves_completed_helpers(self):
        with self.assertRaises(setup.SetupCancelled):
            self.execute(self.helper_answers() + self.shell_answers(False) + ["no"])
        self.assertTrue(self.helpers.exists())
        self.assertEqual(self.profile.read_bytes(), self.original)

    def test_existing_helper_file_can_be_selected_without_rewriting(self):
        contents = b"schema_version = 1\n# Fictional existing settings\n"
        self.helpers.write_bytes(contents)
        self.assertEqual(self.execute(["y", "", "y", "y", str(self.helpers), "n"]), 0)
        self.assertEqual(self.helpers.read_bytes(), contents)

    def test_modified_installation_blocks_optional_changes(self):
        (self.release / "README.md").write_text("Fictional change")
        with mock.patch("builtins.input") as prompt, redirect_stdout(io.StringIO()), \
                mock.patch("sys.stderr", new=io.StringIO()):
            self.assertNotEqual(setup.finish_setup(str(self.plan), cli), 0)
        prompt.assert_not_called()
        self.assertEqual(self.profile.read_bytes(), self.original)

    def test_nonobject_install_plan_is_refused_before_optional_work(self):
        invalid = self.root / "not-an-install-plan.json"
        invalid.write_text("[]")
        with self.assertRaisesRegex(ValueError, "saved installation plan"):
            setup.finish_setup(str(invalid), cli)
        self.assertFalse(list(self.root.glob("byte-config-*")))

    def test_session_script_quotes_shell_metacharacters_and_avoids_duplicate_path(self):
        folder = self.root / "literal ' $(not-a-command)"
        (folder / "shell").mkdir(parents=True)
        (folder / "shell/byte-shell.sh").write_text(":\n")
        wrapper = self.root / "quoted.sh"
        wrapper.write_text(setup.session_script(folder, self.helpers))
        result = subprocess.run(["bash", "--noprofile", "--norc", "-c",
                                 '. "$1"; . "$1"; printf "%s\\n%s\\n" "$PATH" "$BYTE_CORE_HELPERS_CONFIG"',
                                 "fixture", str(wrapper)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0].split(":").count(str(folder / "bin")), 1)
        self.assertEqual(result.stdout.splitlines()[1], str(self.helpers))

    def test_file_publication_refuses_existing_file_and_symlink(self):
        target = self.root / "preserved.txt"
        target.write_text("Fictional original")
        link = self.root / "link"
        link.symlink_to(target)
        for path in (target, link):
            with self.subTest(path=path), self.assertRaises(FileExistsError):
                setup.save_private(path, "replacement")
        self.assertEqual(target.read_text(), "Fictional original")

    def test_main_finish_mode_does_not_reinstall_or_run_location_wizard(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=True), \
                mock.patch.object(setup, "finish_setup", return_value=0) as finish, \
                mock.patch.object(setup, "guide") as guide, mock.patch.object(setup, "run") as run:
            self.assertEqual(setup.main(["--finish-setup", str(self.plan)]), 0)
        finish.assert_called_once()
        guide.assert_not_called()
        run.assert_not_called()

    def test_starter_plan_can_offer_editor_without_reinstalling(self):
        deployment = self.root / "deployment"
        output = io.StringIO()
        self.assertEqual(cli.main(["plan", "init", "--deployment-root", str(deployment)], stdout=output), 0)
        starter = self.root / "init-plan.json"
        starter.write_text(output.getvalue())
        self.assertEqual(cli.main(["apply", "--plan", str(starter)], stdout=io.StringIO()), 0)
        with mock.patch.object(setup.shutil, "which", return_value="/fictional/editor"), \
                mock.patch.object(setup.subprocess, "call", return_value=0) as editor:
            self.assertEqual(self.execute(["y", "", "n", "n", "y", "fictional-editor"], starter_plan=str(starter)), 0)
        editor.assert_called_once_with(["/fictional/editor", str(deployment / "notebook.md")])

    def test_profile_destination_inside_core_is_refused(self):
        with self.assertRaisesRegex(ValueError, "outside Core"):
            self.execute(["y", "", "n", "y", "y", str(self.release)])
        self.assertFalse((self.release / ".bashrc").exists())

    def test_preview_refuses_shared_settings_and_wrapper_destination(self):
        with self.assertRaisesRegex(ValueError, "different files"):
            self.execute(self.helper_answers(False) + ["y", "y", str(self.home), str(self.helpers)], plan_only=True)
        self.assertFalse(self.helpers.exists())

    @unittest.skipUnless(shutil.which("zsh"), "Zsh unavailable")
    def test_zsh_profile_and_command_use_selected_installation(self):
        self.assertEqual(self.execute(["y", "", "n", "y", "n", str(self.home), str(self.wrapper), "y", "APPROVE_SHELL"]), 0)
        result = subprocess.run(["zsh", "-f", "-c", '. "$1"; command -v byte; byte check --format json',
                                 "fixture", str(self.wrapper)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], str(self.release / "bin/byte"))


if __name__ == "__main__":
    unittest.main()
