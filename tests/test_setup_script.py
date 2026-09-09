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

    def test_install_only_does_not_plan_or_create_deployment(self):
        self.args.skip_init = True
        self.args.deployment_root = None
        self.assertEqual(self.execute(("install-review-id",)), 0)
        self.assertEqual([call[0] for call in self.calls], ["check", "plan", "apply", "verify"])
        self.assertEqual(self.calls[1][1], "install")
        self.assertFalse((self.parent / "deployment").exists())

    def test_new_target_created_during_review_stops_both_applies(self):
        def approve(prompt):
            if "init" in prompt:
                Path(self.args.deployment_root).mkdir()
                return "init-review-id"
            return "install-review-id"
        with self.assertRaises(ValueError):
            self.execute(approve)
        self.assertNotIn("apply", [call[0] for call in self.calls])

    def test_yes_does_not_replace_exact_plan_approval(self):
        self.assertEqual(self.execute(("yes",)), 5)
        self.assertNotIn("apply", [call[0] for call in self.calls])

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
                    self.assertIn("lifecycle prerequisites", errors.getvalue())
                    self.assertIn("./bin/byte check", errors.getvalue())


class GuidedSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.args = argparse.Namespace(
            guided=True, version=None, core_root=None, state_root=None,
            deployment_root=None, work_parent=None, skip_init=False, plan_only=False,
        )

    def guide(self, answers):
        with redirect_stdout(io.StringIO()), mock.patch("builtins.input", side_effect=answers):
            return setup.guide(self.args)

    def test_default_guidance_selects_paths_and_preview_without_writes(self):
        args = self.guide(["yes", "", "", str(self.parent), "", "", "yes"])
        self.assertEqual(args.version, "0.1.0")
        self.assertEqual(args.core_root, str(self.parent / "byte-core"))
        self.assertEqual(args.state_root, str(self.parent / "byte-core-state"))
        self.assertEqual(args.deployment_root, str(self.parent / "byte-core-deployment"))
        self.assertTrue(args.plan_only)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_install_only_and_custom_locations(self):
        core, state = self.parent / "program files", self.parent / "state files"
        args = self.guide(["y", "y", "n", str(self.parent), "n", str(core), str(state), "n", "y"])
        self.assertTrue(args.skip_init)
        self.assertIsNone(args.deployment_root)
        self.assertFalse(args.plan_only)
        self.assertEqual(args.core_root, str(core))
        self.assertEqual(args.state_root, str(state))
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_no_or_empty_initial_answer_cancels_without_writes(self):
        for response in ("", "no", "q", "cancel"):
            with self.subTest(response=response), self.assertRaises(setup.SetupCancelled):
                self.guide([response])
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_eof_cancels_without_writes(self):
        with self.assertRaises(setup.SetupCancelled):
            self.guide(EOFError())
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_invalid_yes_no_answer_reprompts(self):
        with mock.patch("builtins.input", side_effect=["maybe", "YES"]), redirect_stdout(io.StringIO()):
            self.assertTrue(setup.yes_no("Continue?"))

    def test_existing_suggested_directory_is_preserved_and_reprompted(self):
        old = self.parent / "byte-core"
        old.mkdir()
        note = old / "note.txt"
        note.write_text("Fictional existing work")
        alternate = self.parent / "another-core"
        args = self.guide(["y", "y", "n", str(self.parent), "y", str(alternate), "y", "y"])
        self.assertEqual(args.core_root, str(alternate))
        self.assertEqual(note.read_text(), "Fictional existing work")
        self.assertFalse(alternate.exists())

    def test_relative_path_and_home_shorthand_reprompt(self):
        with mock.patch("builtins.input", side_effect=["relative", "~/example", str(self.parent)]), redirect_stdout(io.StringIO()):
            self.assertEqual(setup.prompt_path("Parent", existing=True), str(self.parent))

    def test_overlap_reprompts_until_targets_are_disjoint(self):
        same = str(self.parent / "same")
        args = self.guide(["y", "y", "n", str(self.parent), "n", same, same,
                           "n", str(self.parent / "core"), str(self.parent / "state"), "y", "y"])
        self.assertNotEqual(args.core_root, args.state_root)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_missing_arguments_on_nonterminal_refuse_instead_of_prompting(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=False), \
                mock.patch("builtins.input") as prompt, mock.patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                setup.main([])
        self.assertEqual(stopped.exception.code, 2)
        prompt.assert_not_called()

    def test_no_argument_terminal_invocation_starts_wizard(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=True), \
                mock.patch.object(setup, "guide", return_value=self.args) as guide, \
                mock.patch.object(setup, "run", return_value=0) as run:
            self.assertEqual(setup.main([]), 0)
        self.assertTrue(guide.call_args.args[0].guided)
        self.assertIs(run.call_args.args[0], self.args)

    def test_newer_python_three_is_not_rejected_by_wrapper(self):
        with mock.patch.object(sys, "version_info", (3, 15)), \
                mock.patch.object(sys.stdin, "isatty", return_value=True), \
                mock.patch.object(setup, "guide", return_value=self.args), \
                mock.patch.object(setup, "run", return_value=0):
            self.assertEqual(setup.main([]), 0)

    def test_guided_install_requires_exact_ids_and_verifies_real_files(self):
        sys.path.insert(0, str(ROOT / "src"))
        from byte_core import cli
        from build_release_artifact import build
        args = self.guide(["y", "y", "y", str(self.parent), "y", "n", "y"])
        def approve(prompt):
            if "complete saved plans" in prompt:
                return "no"
            if "Continue with optional configuration" in prompt:
                return "no"
            name = "init" if "init" in prompt else "install"
            plan = next(self.parent.glob(f"byte-setup-*/{name}-plan.json"))
            return json.loads(plan.read_text())["plan_id"]
        report = cli.CheckReport("check", True, ())
        with mock.patch.object(cli, "collect_check_report", return_value=report), \
                mock.patch.object(setup, "check_launcher_readiness", return_value=0), \
                mock.patch("builtins.input", side_effect=approve), redirect_stdout(io.StringIO()):
            self.assertEqual(setup.run(args, cli, build), 0)
        self.assertTrue((Path(args.state_root) / "installation.json").is_file())
        self.assertEqual(len(list(Path(args.deployment_root).iterdir())), 5)


class RepositoryDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.args = argparse.Namespace(repository=None, ref=None,
                                       source_parent=str(self.parent), download_only=False)
        self.commit = "a" * 40
        self.commands = []

    def fake_git(self, source, *args):
        self.commands.append(args)
        if args[0] == "checkout":
            for directory in ("src/byte_core", "scripts", "bin", "docs/release-notes"):
                (source / directory).mkdir(parents=True, exist_ok=True)
            for name in ("src/byte_core/__init__.py", "src/byte_core/cli.py",
                         "scripts/build_release_artifact.py", "bin/byte"):
                (source / name).write_text("# Fictional source fixture\n")
        return self.commit if args[0] == "rev-parse" else ""

    def download(self, answers=("", "yes", "yes")):
        with mock.patch.object(setup.shutil, "which", return_value="/fictional/git"), \
                mock.patch.object(setup, "source_git", side_effect=self.fake_git), \
                mock.patch("builtins.input", side_effect=answers), redirect_stdout(io.StringIO()):
            return setup.download_source(self.args)

    def test_download_resolves_detached_commit_and_records_identity(self):
        source = self.download()
        self.assertTrue(source.is_dir())
        self.assertIn(("remote", "add", "origin", "https://github.com/Lakoswolf/byte-core-Testing.git"), self.commands)
        self.assertIn(("checkout", "--quiet", "--detach", self.commit), self.commands)
        record = source.parent / "source.json"
        self.assertEqual(json.loads(record.read_text()), {
            "repository": setup.DEFAULT_REPOSITORY, "requested_ref": "HEAD", "commit": self.commit,
        })
        self.assertEqual(record.stat().st_mode & 0o777, 0o600)
        self.assertEqual(source.parent.stat().st_mode & 0o777, 0o700)

    def test_repository_and_ref_are_configurable(self):
        self.args.repository = "fictional-owner/example-core"
        self.args.ref = "refs/heads/review"
        self.download()
        self.assertIn(("remote", "add", "origin", "https://github.com/fictional-owner/example-core.git"), self.commands)
        self.assertEqual(next(args for args in self.commands if args[0] == "fetch")[-1], self.args.ref)

    def test_download_only_never_requests_code_execution(self):
        self.args.download_only = True
        self.assertIsNone(self.download(("", "yes")))
        self.assertEqual(len(list(self.parent.glob("byte-source-*/source.json"))), 1)

    def test_download_cancellation_creates_nothing(self):
        with self.assertRaises(setup.SetupCancelled):
            self.download(("", "no"))
        self.assertEqual(self.commands, [])
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_execution_cancellation_preserves_download(self):
        with self.assertRaises(setup.SetupCancelled):
            self.download(("", "yes", "no"))
        self.assertEqual(len(list(self.parent.glob("byte-source-*/source.json"))), 1)

    def test_missing_git_stops_before_download(self):
        with mock.patch.object(setup.shutil, "which", return_value=None), \
                mock.patch.object(setup, "source_git") as git:
            with self.assertRaisesRegex(RuntimeError, "requires Git"):
                setup.download_source(self.args)
        git.assert_not_called()

    def test_credentials_urls_and_option_like_inputs_are_refused(self):
        for value in ("https://github.com/example/core", "user:secret@example/core", "--option/core", "../core", "example/core\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                setup.repository_url(value)
        for value in ("--upload-pack=anything", "main:other", "../main", "main..other", "main\n", "$(command)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                setup.repository_ref(value)

    def test_revision_change_or_dirty_source_is_refused(self):
        source = self.download()
        for results in (("b" * 40,), (self.commit, " M src/byte_core/cli.py")):
            with self.subTest(results=results), mock.patch.object(setup, "source_git", side_effect=results):
                with self.assertRaises(ValueError):
                    setup.verify_source(source, self.commit)

    def test_required_source_symlink_is_refused(self):
        source = self.download()
        target = source / "src/byte_core/cli.py"
        renamed = target.with_name("original.py")
        target.rename(renamed)
        target.symlink_to(renamed)
        with mock.patch.object(setup, "source_git", side_effect=(self.commit, "")):
            with self.assertRaisesRegex(ValueError, "source layout"):
                setup.verify_source(source, self.commit)

    def test_git_timeout_and_errors_are_bounded_without_raw_diagnostics(self):
        for outcome in (subprocess.TimeoutExpired("git", 300), mock.Mock(returncode=1)):
            with self.subTest(outcome=type(outcome).__name__), mock.patch.object(setup.subprocess, "run") as run:
                if isinstance(outcome, Exception):
                    run.side_effect = outcome
                else:
                    run.return_value = outcome
                with self.assertRaises(RuntimeError):
                    setup.source_git(self.parent, "fetch", "origin", "HEAD")
                self.assertEqual(run.call_args.kwargs["timeout"], 300)
                self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)

    def test_git_does_not_inherit_repository_redirection(self):
        with mock.patch.dict("os.environ", {"GIT_DIR": "/fictional/other", "GIT_CONFIG_COUNT": "1"}), \
                mock.patch.object(setup.subprocess, "run", return_value=mock.Mock(returncode=0, stdout="")) as run:
            setup.source_git(self.parent, "init", "--quiet")
        env = run.call_args.kwargs["env"]
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GIT_CONFIG_COUNT", env)
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertIn("core.hooksPath=" + setup.os.devnull, run.call_args.args[0])

    def test_standalone_script_location_is_not_mistaken_for_a_checkout(self):
        with mock.patch.object(setup, "REPOSITORY_ROOT", self.parent):
            self.assertEqual(setup.selected_path(str(self.parent), existing=True), self.parent)

    def test_existing_parent_may_contain_checkout_but_cannot_be_inside_it(self):
        self.assertEqual(setup.selected_path(str(ROOT.parent), existing=True), ROOT.parent)
        for path in (ROOT, ROOT / "scripts"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                setup.selected_path(str(path), existing=True)

    def test_download_only_main_does_not_run_wizard(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=True), \
                mock.patch.object(setup, "download_source", return_value=None) as download, \
                mock.patch.object(setup, "guide") as guide, mock.patch.object(setup, "run") as run:
            self.assertEqual(setup.main(["--download-only"]), 0)
        download.assert_called_once()
        guide.assert_not_called()
        run.assert_not_called()
