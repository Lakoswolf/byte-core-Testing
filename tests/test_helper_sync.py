"""Fictional local Git repositories only; no network or user repository mutation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from byte_core import helper_sync as sync


@unittest.skipUnless(shutil.which("git"), "Git unavailable")
class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.environment = {key: value for key, value in os.environ.items()
                            if not key.startswith("GIT_")}
        self.environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                                HOME=str(self.root), XDG_CONFIG_HOME=str(self.root / "config"),
                                GIT_AUTHOR_NAME="Fictional Example", GIT_AUTHOR_EMAIL="example@example.invalid",
                                GIT_COMMITTER_NAME="Fictional Example", GIT_COMMITTER_EMAIL="example@example.invalid")
        # Isolate Git configuration without inspecting real operator configuration.
        self.env_patch = mock.patch.dict(os.environ, self.environment, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.remote = self.root / "fictional-remote.git"
        self.seed = self.root / "fictional-seed"
        self.local = self.root / "fictional-work"
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "main", str(self.seed))
        self.commit(self.seed, "first")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "main")
        self.git(self.root, "clone", "-b", "main", str(self.remote), str(self.local))
        self.config = {"repositories": [{"name": "fictional", "path": str(self.local),
                                         "remote": "origin", "branch": "main"}]}

    def git(self, path, *arguments):
        result = subprocess.run(["git", "-C", str(path), *arguments], check=True,
                                capture_output=True, text=True, env=self.environment)
        return result.stdout.strip()

    def commit(self, path, name):
        (path / (name + ".txt")).write_text("Fresh fictional fixture.\n")
        self.git(path, "add", "--", name + ".txt")
        self.git(path, "commit", "-m", "Fictional " + name)
        return self.git(path, "rev-parse", "HEAD")

    def advance(self):
        tip = self.commit(self.seed, "second")
        self.git(self.seed, "push", "origin", "main")
        return tip

    def test_plan_offline_and_apply_fast_forward(self):
        wanted = self.advance()
        before = self.git(self.local, "rev-parse", "HEAD")
        with mock.patch.object(sync, "_git", wraps=sync._git) as git:
            proposed = sync.plan(self.config)
        self.assertFalse(any(call.args[1] == "fetch" for call in git.call_args_list))
        self.assertEqual(before, self.git(self.local, "rev-parse", "HEAD"))
        self.assertEqual(proposed, json.loads(json.dumps(proposed)))
        result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(wanted, self.git(self.local, "rev-parse", "HEAD"))
        self.assertEqual(result["repositories"][0]["starting_sha"], before)

    def test_switch_existing_branch_then_fast_forward(self):
        self.git(self.local, "switch", "-c", "topic")
        wanted = self.advance()
        proposed = sync.plan(self.config)
        result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(self.git(self.local, "branch", "--show-current"), "main")
        self.assertEqual(self.git(self.local, "rev-parse", "HEAD"), wanted)
        self.assertEqual(result["repositories"][0]["switch"], "complete")

    def test_dirty_detached_and_in_progress_refused(self):
        (self.local / "untracked").write_text("fictional")
        with self.assertRaisesRegex(sync.SyncError, "dirty"):
            sync.plan(self.config)
        (self.local / "untracked").unlink()
        self.git(self.local, "switch", "--detach")
        with self.assertRaisesRegex(sync.SyncError, "detached"):
            sync.plan(self.config)
        self.git(self.local, "switch", "main")
        (self.local / ".git" / "MERGE_HEAD").write_text(self.git(self.local, "rev-parse", "HEAD"))
        with self.assertRaisesRegex(sync.SyncError, "in_progress"):
            sync.plan(self.config)

    def test_other_worktree_rejected(self):
        self.git(self.local, "switch", "-c", "topic")
        self.git(self.local, "worktree", "add", str(self.root / "fictional-other"), "main")
        with self.assertRaisesRegex(sync.SyncError, "other_worktree"):
            sync.plan(self.config)

    def test_stale_state_and_wrong_approval_do_not_fetch(self):
        proposed = sync.plan(self.config)
        with self.assertRaisesRegex(sync.SyncError, "not_approved"):
            sync.apply(self.config, proposed, "wrong")
        self.commit(self.local, "local")
        with mock.patch.object(sync, "_git", wraps=sync._git) as git:
            with self.assertRaisesRegex(sync.SyncError, "stale"):
                sync.apply(self.config, proposed, proposed["id"])
        self.assertFalse(any(call.args[1] == "fetch" for call in git.call_args_list))

    def test_config_and_plan_tampering_refused(self):
        proposed = sync.plan(self.config)
        changed = dict(self.config, unrelated_preference=True)
        with self.assertRaisesRegex(sync.SyncError, "stale"):
            sync.apply(changed, proposed, proposed["id"])
        proposed["operations"] = []
        with self.assertRaisesRegex(sync.SyncError, "not_approved"):
            sync.apply(self.config, proposed, proposed["id"])

    def test_divergence_preserves_head_and_reports_fetch(self):
        self.advance()
        before = self.commit(self.local, "diverged")
        proposed = sync.plan(self.config)
        result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["error"], "sync_fast_forward_unavailable")
        self.assertEqual(result["repositories"][0]["fetch"], "complete")
        self.assertEqual(self.git(self.local, "rev-parse", "HEAD"), before)

    def test_second_fetch_failure_records_partial_progress(self):
        other = self.root / "fictional-second"
        self.git(self.root, "clone", "-b", "main", str(self.remote), str(other))
        self.config["repositories"].append(dict(self.config["repositories"][0],
                                                 name="second", path=str(other)))
        proposed = sync.plan(self.config)
        original = sync._git
        def fail(path, *args, **kwargs):
            if str(path) == str(other) and args[0] == "fetch":
                raise sync.SyncError("sync_git_timeout")
            return original(path, *args, **kwargs)
        with mock.patch.object(sync, "_git", side_effect=fail):
            result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["repositories"][0]["fetch"], "complete")
        self.assertEqual(result["repositories"][1]["fetch"], "attempted_may_have_changed_refs")
        self.assertTrue(all(item["update"] == "not_started" for item in result["repositories"]))

    def test_merge_failure_after_switch_is_reported(self):
        self.git(self.local, "switch", "-c", "topic")
        self.advance()
        proposed = sync.plan(self.config)
        original = sync._git
        def fail(path, *args, **kwargs):
            if args[0] == "merge":
                raise sync.SyncError("sync_git_failed")
            return original(path, *args, **kwargs)
        with mock.patch.object(sync, "_git", side_effect=fail):
            result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["repositories"][0]["switch"], "complete")
        self.assertEqual(result["repositories"][0]["observed_branch"], "refs/heads/main")
        self.assertEqual(result["repositories"][0]["starting_branch"], "refs/heads/topic")

    def test_option_injection_and_nonroot_refused(self):
        for key, value in (("branch", "--orphan"), ("branch", "@{-1}"), ("remote", "--upload-pack=bad")):
            with self.subTest(key=key, value=value):
                config = {"repositories": [dict(self.config["repositories"][0], **{key: value})]}
                with self.assertRaises(sync.SyncError):
                    sync.plan(config)
        nested = self.local / "nested"
        nested.mkdir()
        config = {"repositories": [dict(self.config["repositories"][0], path=str(nested))]}
        with self.assertRaisesRegex(sync.SyncError, "root_required"):
            sync.plan(config)

    def test_timeout_and_no_raw_git_error(self):
        original = subprocess.Popen
        def execute(code):
            return lambda argv, **kwargs: original([sys.executable, "-c", code], **kwargs)
        started = time.monotonic()
        with mock.patch.object(sync, "TIMEOUT_SECONDS", 0.1), \
                mock.patch.object(sync.subprocess, "Popen", side_effect=execute("import time; time.sleep(10)")):
            with self.assertRaisesRegex(sync.SyncError, "sync_git_timeout"):
                sync._git(self.local, "status")
        self.assertLess(time.monotonic() - started, 3)
        with mock.patch.object(sync.subprocess, "Popen", side_effect=execute(
                "import sys; sys.stderr.write('untrusted detail'); sys.exit(128)")):
            with self.assertRaisesRegex(sync.SyncError, "^sync_git_failed$"):
                sync._git(self.local, "status")

    def test_output_bound_stops_process(self):
        original = subprocess.Popen
        def oversized(argv, **kwargs):
            return original([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * (3 * 1024 * 1024))"], **kwargs)
        with mock.patch.object(sync.subprocess, "Popen", side_effect=oversized):
            with self.assertRaisesRegex(sync.SyncError, "sync_git_output_limit"):
                sync._git(self.local, "status")

    def test_offline_plan_refuses_filters_before_any_status(self):
        for operation in ("clean", "smudge", "process"):
            with self.subTest(operation=operation):
                self.git(self.local, "config", "filter.fictional." + operation, "false")
                with mock.patch.object(sync, "_git", wraps=sync._git) as git:
                    with self.assertRaisesRegex(sync.SyncError, "filters_unsupported"):
                        sync.plan(self.config)
                self.assertFalse(any(call.args[1] == "status" for call in git.call_args_list))
                self.git(self.local, "config", "--unset", "filter.fictional." + operation)

    def test_offline_plan_refuses_promisor_before_object_reads(self):
        for key, value in (("remote.origin.promisor", "true"), ("extensions.partialClone", "origin")):
            with self.subTest(key=key):
                self.git(self.local, "config", key, value)
                with mock.patch.object(sync, "_git", wraps=sync._git) as git:
                    with self.assertRaisesRegex(sync.SyncError, "partial_clone_unsupported"):
                        sync.plan(self.config)
                self.assertFalse(any(call.args[1] in {"status", "rev-parse"} for call in git.call_args_list))
                self.git(self.local, "config", "--unset", key)

    def test_offline_plan_refuses_indexed_submodules_before_status(self):
        tip = self.git(self.local, "rev-parse", "HEAD")
        self.git(self.local, "update-index", "--add", "--cacheinfo", "160000," + tip + ",fictional-submodule")
        with mock.patch.object(sync, "_git", wraps=sync._git) as git:
            with self.assertRaisesRegex(sync.SyncError, "submodules_unsupported"):
                sync.plan(self.config)
        self.assertFalse(any(call.args[1] == "status" for call in git.call_args_list))

    def test_replaced_repository_refused_before_fetch(self):
        proposed = sync.plan(self.config)
        preserved = self.root / "fictional-preserved-original"
        self.local.rename(preserved)
        shutil.copytree(preserved, self.local)
        with mock.patch.object(sync, "_git", wraps=sync._git) as git:
            with self.assertRaisesRegex(sync.SyncError, "stale"):
                sync.apply(self.config, proposed, proposed["id"])
        self.assertFalse(any(call.args[1] == "fetch" for call in git.call_args_list))

    def test_symlink_ancestor_refused(self):
        link = self.root / "fictional-link"
        link.symlink_to(self.root, target_is_directory=True)
        self.config["repositories"][0]["path"] = str(link / self.local.name)
        with self.assertRaisesRegex(sync.SyncError, "path_invalid"):
            sync.plan(self.config)

    def test_branch_merge_options_refused_before_status(self):
        self.git(self.local, "config", "branch.main.mergeOptions", "--squash")
        with mock.patch.object(sync, "_git", wraps=sync._git) as git:
            with self.assertRaisesRegex(sync.SyncError, "merge_options_unsupported"):
                sync.plan(self.config)
        self.assertFalse(any(call.args[1] in {"status", "fetch"} for call in git.call_args_list))

    def test_ignored_file_is_preserved_when_fast_forward_would_replace_it(self):
        self.advance()
        ignored = self.local / "second.txt"
        original = "Fictional operator content must remain.\n"
        ignored.write_text(original)
        (self.local / ".git" / "info" / "exclude").write_text("second.txt\n")
        before = self.git(self.local, "rev-parse", "HEAD")
        proposed = sync.plan(self.config)
        result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "partial", result)
        self.assertEqual(ignored.read_text(), original)
        self.assertEqual(self.git(self.local, "rev-parse", "HEAD"), before)

    def test_ignored_file_is_preserved_when_switch_would_replace_it(self):
        self.git(self.local, "switch", "-c", "topic")
        self.git(self.local, "rm", "first.txt")
        self.git(self.local, "commit", "-m", "Fictional removed file")
        ignored = self.local / "first.txt"
        original = "Fictional operator content must remain.\n"
        ignored.write_text(original)
        (self.local / ".git" / "info" / "exclude").write_text("first.txt\n")
        proposed = sync.plan(self.config)
        result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "partial", result)
        self.assertEqual(ignored.read_text(), original)
        self.assertEqual(self.git(self.local, "branch", "--show-current"), "topic")

    def test_merge_disables_automatic_stashing(self):
        self.git(self.local, "config", "merge.autoStash", "true")
        self.advance()
        proposed = sync.plan(self.config)
        original = sync._git
        def change_before_merge(path, *args, **kwargs):
            if args[0] == "merge":
                self.assertIn("--no-autostash", args)
                (self.local / "first.txt").write_text("Fictional concurrent edit.\n")
            return original(path, *args, **kwargs)
        with mock.patch.object(sync, "_git", side_effect=change_before_merge):
            result = sync.apply(self.config, proposed, proposed["id"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(self.git(self.local, "stash", "list"), "")
        self.assertEqual((self.local / "first.txt").read_text(), "Fictional concurrent edit.\n")


if __name__ == "__main__":
    unittest.main()
