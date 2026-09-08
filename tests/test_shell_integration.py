from __future__ import annotations

import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
SHELL_SCRIPT = REPOSITORY_ROOT / "shell" / "byte-shell.sh"
sys.path.insert(0, str(SOURCE_ROOT))

from byte_core.shell_integration import (  # noqa: E402
    END_MARKER,
    MAX_PROFILE_BYTES,
    START_MARKER,
    ShellIntegrationError,
    apply_shell_plan,
    build_shell_install_plan,
    build_shell_removal_plan,
    load_shell_plan,
    serialize_shell_plan,
    verify_shell_plan,
)


class ShellIntegrationTests(unittest.TestCase):
    def test_bash_install_verify_replay_and_remove_preserve_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            profile = home / ".bashrc"
            original = b"# operator content\nexport FICTIONAL_VALUE=yes\n"
            profile.write_bytes(original)
            profile.chmod(0o640)
            install = build_shell_install_plan(home, "bash", SHELL_SCRIPT)

            applied = apply_shell_plan(install)

            self.assertEqual(applied.code, "integrated")
            self.assertEqual(verify_shell_plan(install).code, "verified")
            self.assertEqual(apply_shell_plan(install).code, "already_integrated")
            self.assertTrue(profile.read_bytes().startswith(original))
            self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o640)
            apply_backup = Path(applied.backup_path)
            self.assertEqual(apply_backup.read_bytes(), original)
            self.assertEqual(stat.S_IMODE(apply_backup.stat().st_mode), 0o600)

            removal = build_shell_removal_plan(home, "bash")
            removed = apply_shell_plan(removal)

            self.assertEqual(removed.code, "removed")
            self.assertEqual(profile.read_bytes(), original)
            self.assertEqual(verify_shell_plan(removal).code, "verified")
            self.assertEqual(apply_shell_plan(removal).code, "already_removed")
            self.assertNotEqual(removed.backup_path, applied.backup_path)
            self.assertIn(START_MARKER, Path(removed.backup_path).read_text())

    def test_new_profiles_and_missing_trailing_newlines_restore_exactly(self) -> None:
        for original in (None, b"operator setting", b"operator setting\n"):
            with self.subTest(original=original):
                with tempfile.TemporaryDirectory() as temporary:
                    home = Path(temporary)
                    profile = home / ".bashrc"
                    if original is not None:
                        profile.write_bytes(original)
                    install = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
                    apply_shell_plan(install)
                    removal = build_shell_removal_plan(home, "bash")
                    apply_shell_plan(removal)

                    if original is None:
                        self.assertFalse(profile.exists())
                    else:
                        self.assertEqual(profile.read_bytes(), original)

    def test_removal_preserves_unrelated_non_utf8_profile_bytes(self) -> None:
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary).resolve()
                profile = home / (".bashrc" if shell == "bash" else ".zshrc")
                original = b"# fictional legacy comment: caf\xe9\n"
                later = b"# unrelated later comment: \xff\xfe\n"
                profile.write_bytes(original)
                profile.chmod(0o640)
                install = build_shell_install_plan(home, shell, SHELL_SCRIPT)
                apply_shell_plan(install)
                self.assertEqual(verify_shell_plan(install).code, "verified")
                self.assertEqual(apply_shell_plan(install).code, "already_integrated")
                profile.write_bytes(profile.read_bytes() + later)
                removal = build_shell_removal_plan(home, shell)
                removed = apply_shell_plan(removal)
                self.assertEqual(profile.read_bytes(), original + later)
                self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o640)
                self.assertEqual(verify_shell_plan(removal).code, "verified")
                self.assertEqual(apply_shell_plan(removal).code, "already_removed")
                self.assertTrue(Path(removed.backup_path).read_bytes().endswith(later))

    def test_byte_level_markers_and_invalid_managed_encoding_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            profile = home / ".bashrc"
            install = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            block = install.managed_block.encode("utf-8")
            variants = (
                b"# unrelated \xff\n" + block + block,
                END_MARKER.encode() + b"\n" + block,
                b"# unrelated \xff" + block,
                block.rstrip(b"\n") + b"trailing \xff\n",
                block.replace(b". '", b". '\xff", 1),
            )
            for content in variants:
                with self.subTest(content=content):
                    profile.write_bytes(content)
                    with self.assertRaisesRegex(ShellIntegrationError, "malformed_managed_block"):
                        build_shell_removal_plan(home, "bash")
                    self.assertEqual(profile.read_bytes(), content)
                    self.assertFalse((home / ".byte-backups").exists())

    def test_oversized_result_refuses_planning_without_profile_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            profile = home / ".bashrc"
            original = b"#" * MAX_PROFILE_BYTES
            profile.write_bytes(original)
            with self.assertRaisesRegex(ShellIntegrationError, "file_too_large"):
                build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            self.assertEqual(profile.read_bytes(), original)
            self.assertFalse((home / ".byte-backups").exists())

    def test_rehashed_oversized_result_plan_refuses_before_backup_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            profile = home / ".bashrc"
            profile.write_bytes(b"# fictional comment")
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            original = b"#" * MAX_PROFILE_BYTES
            profile.write_bytes(original)
            raw = json.loads(serialize_shell_plan(plan))
            raw["original_sha256"] = hashlib.sha256(original).hexdigest()
            raw["result_sha256"] = hashlib.sha256(
                original + b"\n\n" + plan.managed_block.encode("utf-8")
            ).hexdigest()
            raw.pop("plan_id")
            raw["plan_id"] = hashlib.sha256(
                json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            path = home / "oversized-plan.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = load_shell_plan(path)
            with self.assertRaisesRegex(ShellIntegrationError, "file_too_large"):
                apply_shell_plan(loaded)
            self.assertEqual(profile.read_bytes(), original)
            self.assertFalse((home / ".byte-backups").exists())

    def test_result_at_profile_limit_can_verify_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            profile = home / ".bashrc"
            profile.write_bytes(b"# fictional comment\n")
            baseline = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            original_size = MAX_PROFILE_BYTES - len(baseline.managed_block.encode("utf-8")) - 1
            original = b"#" * (original_size - 1) + b"\n"
            profile.write_bytes(original)
            install = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            apply_shell_plan(install)
            self.assertEqual(profile.stat().st_size, MAX_PROFILE_BYTES)
            self.assertEqual(verify_shell_plan(install).code, "verified")
            removal = build_shell_removal_plan(home, "bash")
            apply_shell_plan(removal)
            self.assertEqual(profile.read_bytes(), original)
            self.assertEqual(verify_shell_plan(removal).code, "verified")

    def test_zsh_syntax_highlighting_is_explicit_and_optional(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            syntax = home / "fictional-syntax-highlighting.zsh"
            syntax.write_text(
                "FICTIONAL_SYNTAX_HIGHLIGHTING=enabled\n", encoding="utf-8"
            )
            without = build_shell_install_plan(home, "zsh", SHELL_SCRIPT)
            self.assertIsNone(without.syntax_highlighting_path)

            with_syntax = build_shell_install_plan(
                home, "zsh", SHELL_SCRIPT, syntax
            )
            self.assertEqual(
                with_syntax.syntax_highlighting_path, str(syntax.resolve())
            )
            apply_shell_plan(with_syntax)
            content = (home / ".zshrc").read_text(encoding="utf-8")
            self.assertIn(str(syntax.resolve()), content)

            other_home = home / "other"
            other_home.mkdir()
            with self.assertRaisesRegex(
                ShellIntegrationError, "syntax_highlighting_requires_zsh"
            ):
                build_shell_install_plan(
                    other_home, "bash", SHELL_SCRIPT, syntax
                )

    def test_conflicting_malformed_and_changed_profiles_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            profile = home / ".bashrc"
            profile.write_text(START_MARKER + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ShellIntegrationError, "managed_block_conflict"
            ):
                build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            with self.assertRaisesRegex(
                ShellIntegrationError, "malformed_managed_block"
            ):
                build_shell_removal_plan(home, "bash")

            profile.write_text("operator content\n", encoding="utf-8")
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            profile.write_text("changed after planning\n", encoding="utf-8")
            with self.assertRaisesRegex(ShellIntegrationError, "profile_changed"):
                apply_shell_plan(plan)
            self.assertFalse((home / ".byte-backups").exists())

    def test_plan_round_trip_and_tampering_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            path = home / "plan.json"
            path.write_text(serialize_shell_plan(plan), encoding="utf-8")
            self.assertEqual(load_shell_plan(path), plan)

            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["profile_path"] = str(home / ".zshrc")
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ShellIntegrationError):
                load_shell_plan(path)

    def test_linked_profiles_and_ambiguous_failures_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = home / "target"
            target.write_text("outside profile\n", encoding="utf-8")
            profile = home / ".bashrc"
            try:
                profile.symlink_to(target)
            except (NotImplementedError, OSError):
                return
            with self.assertRaisesRegex(ShellIntegrationError, "invalid_profile"):
                build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            self.assertEqual(target.read_text(encoding="utf-8"), "outside profile\n")

            profile.unlink()
            profile.write_text("operator content\n", encoding="utf-8")
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)

            def make_ambiguous(active_plan):
                profile.write_text("changed during verification\n", encoding="utf-8")
                raise ShellIntegrationError("profile_changed")

            with mock.patch(
                "byte_core.shell_integration._verify_result",
                side_effect=make_ambiguous,
            ):
                with self.assertRaisesRegex(
                    ShellIntegrationError, "recovery_required"
                ):
                    apply_shell_plan(plan)
            self.assertEqual(
                profile.read_text(encoding="utf-8"),
                "changed during verification\n",
            )
            self.assertTrue(Path(
                home / ".byte-backups"
                / f".bashrc.{plan.plan_id}.shell_install.bak"
            ).is_file())

    def test_plan_binds_selected_native_asset_and_source_changes_change_id(self) -> None:
        for shell, native_name in (("bash", "byte-shell-bash.sh"), ("zsh", "byte-shell-zsh.zsh")):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                plan = build_shell_install_plan(home, shell, SHELL_SCRIPT)
                expected = (SHELL_SCRIPT, SHELL_SCRIPT.with_name(native_name))
                self.assertEqual(tuple(source.path for source in plan.source_files),
                                 tuple(str(path) for path in expected))
                for source, path in zip(plan.source_files, expected):
                    self.assertEqual(source.sha256, hashlib.sha256(path.read_bytes()).hexdigest())
                    self.assertEqual(source.mode, stat.S_IMODE(path.stat().st_mode))
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            script = home / "fictional-source.sh"
            script.write_text("# first source\n", encoding="utf-8")
            script.chmod(0o640)
            first = build_shell_install_plan(home, "bash", script)
            script.write_text("# second source\n", encoding="utf-8")
            second = build_shell_install_plan(home, "bash", script)
            script.chmod(0o600)
            third = build_shell_install_plan(home, "bash", script)
            self.assertEqual(len({first.plan_id, second.plan_id, third.plan_id}), 3)
            self.assertEqual(first.managed_block, third.managed_block)

    def test_profile_permission_drift_refuses_apply_replay_and_verify(self) -> None:
        for installed in (False, True):
            with self.subTest(installed=installed), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                profile = home / ".bashrc"
                profile.write_bytes(b"operator content\n")
                profile.chmod(0o640)
                plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
                if installed:
                    apply_shell_plan(plan)
                content = profile.read_bytes()
                profile.chmod(0o600)
                with self.assertRaisesRegex(ShellIntegrationError, "profile_changed"):
                    apply_shell_plan(plan)
                with self.assertRaisesRegex(ShellIntegrationError, "verification_failed"):
                    verify_shell_plan(plan)
                self.assertEqual(profile.read_bytes(), content)
                self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o600)
                self.assertEqual((home / ".byte-backups").exists(), installed)

    def test_new_profile_mode_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            apply_shell_plan(plan)
            self.assertEqual(stat.S_IMODE((home / ".bashrc").stat().st_mode), 0o600)

    def test_source_content_modes_and_missing_files_refuse_stale_plans(self) -> None:
        for target in ("script", "native", "syntax"):
            for change in ("content", "mode", "missing"):
                for installed in (False, True):
                    with self.subTest(target=target, change=change, installed=installed):
                        with tempfile.TemporaryDirectory() as temporary:
                            home = Path(temporary)
                            script = home / "byte-shell.sh"
                            native = home / "byte-shell-zsh.zsh"
                            syntax = home / "fictional-highlight.zsh"
                            for path in (script, native, syntax):
                                path.write_text("# fictional source\n", encoding="utf-8")
                                path.chmod(0o640)
                            plan = build_shell_install_plan(home, "zsh", script, syntax)
                            self.assertEqual(len(plan.source_files), 3)
                            if installed:
                                apply_shell_plan(plan)
                            profile = home / ".zshrc"
                            before = profile.read_bytes() if installed else None
                            path = {"script": script, "native": native, "syntax": syntax}[target]
                            if change == "content":
                                path.write_text("# changed source\n", encoding="utf-8")
                            elif change == "mode":
                                path.chmod(0o600)
                            else:
                                path.unlink()
                            with self.assertRaisesRegex(ShellIntegrationError, "source_changed"):
                                apply_shell_plan(plan)
                            with self.assertRaisesRegex(ShellIntegrationError, "verification_failed"):
                                verify_shell_plan(plan)
                            self.assertEqual(profile.read_bytes() if profile.exists() else None, before)
                            self.assertEqual((home / ".byte-backups").exists(), installed)

    def test_removal_does_not_require_live_source_code(self) -> None:
        for missing_before_plan in (False, True):
            with self.subTest(missing_before_plan=missing_before_plan):
                with tempfile.TemporaryDirectory() as temporary:
                    home = Path(temporary)
                    script = home / "byte-shell.sh"
                    native = home / "byte-shell-zsh.zsh"
                    syntax = home / "fictional-highlight.zsh"
                    for path in (script, native, syntax):
                        path.write_text("# fictional source\n", encoding="utf-8")
                    profile = home / ".zshrc"
                    original = b"# unrelated operator bytes\n"
                    profile.write_bytes(original)
                    profile.chmod(0o640)
                    install = build_shell_install_plan(home, "zsh", script, syntax)
                    apply_shell_plan(install)
                    profile.write_bytes(profile.read_bytes() + b"# later unrelated setting\n")
                    if missing_before_plan:
                        for path in (script, native, syntax):
                            path.unlink()
                    removal = build_shell_removal_plan(home, "zsh")
                    self.assertEqual(removal.source_files, ())
                    if not missing_before_plan:
                        for path in (script, native, syntax):
                            path.unlink()
                    plan_path = home / "removal.json"
                    plan_path.write_text(serialize_shell_plan(removal), encoding="utf-8")
                    self.assertEqual(load_shell_plan(plan_path), removal)
                    apply_shell_plan(removal)
                    self.assertEqual(verify_shell_plan(removal).code, "verified")
                    self.assertEqual(apply_shell_plan(removal).code, "already_removed")
                    self.assertEqual(profile.read_bytes(), original + b"# later unrelated setting\n")
                    self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o640)

    def test_removal_permission_drift_preserves_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            apply_shell_plan(build_shell_install_plan(home, "bash", SHELL_SCRIPT))
            plan = build_shell_removal_plan(home, "bash")
            profile = home / ".bashrc"
            original = profile.read_bytes()
            profile.chmod(0o644)
            with self.assertRaisesRegex(ShellIntegrationError, "profile_changed"):
                apply_shell_plan(plan)
            self.assertEqual(profile.read_bytes(), original)

    def test_missing_native_asset_refuses_planning_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            script = home / "byte-shell.sh"
            script.write_text("# fictional core entrypoint\n", encoding="utf-8")
            with self.assertRaisesRegex(ShellIntegrationError, "invalid_source_file"):
                build_shell_install_plan(home, "bash", script)
            self.assertEqual(list(home.iterdir()), [script])

    def test_read_only_checks_leave_profile_and_backup_state_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            self.assertEqual(list(home.iterdir()), [])
            apply_shell_plan(plan)
            def snapshot():
                return {str(path.relative_to(home)): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                        for path in home.rglob("*") if path.is_file()}
            before = snapshot()
            verify_shell_plan(plan)
            build_shell_removal_plan(home, "bash")
            self.assertEqual(snapshot(), before)

    def test_source_change_during_apply_restores_profile_from_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            script = home / "fictional-source.sh"
            script.write_text("# original source\n", encoding="utf-8")
            profile = home / ".bashrc"
            profile.write_bytes(b"# original profile\n")
            profile.chmod(0o640)
            plan = build_shell_install_plan(home, "bash", script)
            from byte_core import shell_integration
            verify = shell_integration._verify_result
            def change_then_verify(active_plan):
                script.write_text("# changed source\n", encoding="utf-8")
                verify(active_plan)
            with mock.patch("byte_core.shell_integration._verify_result", side_effect=change_then_verify):
                with self.assertRaisesRegex(ShellIntegrationError, "source_changed"):
                    apply_shell_plan(plan)
            self.assertEqual(profile.read_bytes(), b"# original profile\n")
            self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o640)
            self.assertEqual(len(list((home / ".byte-backups").iterdir())), 1)

    def test_mode_change_during_verification_preserved_for_manual_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            profile = home / ".bashrc"
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            def change_mode(active_plan):
                profile.chmod(0o644)
                raise ShellIntegrationError("profile_changed")
            with mock.patch("byte_core.shell_integration._verify_result", side_effect=change_mode):
                with self.assertRaisesRegex(ShellIntegrationError, "recovery_required"):
                    apply_shell_plan(plan)
            self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o644)
            self.assertIn(START_MARKER, profile.read_text(encoding="utf-8"))

    def test_legacy_and_malformed_source_plans_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            plan = build_shell_install_plan(home, "bash", SHELL_SCRIPT)
            path = home / "plan.json"
            base = json.loads(serialize_shell_plan(plan))
            variants = [
                {**base, "schema_version": 1},
                {key: value for key, value in base.items() if key != "source_files"},
                {**base, "source_files": []},
                {**base, "source_files": [None]},
                {**base, "source_files": [{"path": 3, "sha256": "0" * 64, "mode": 384}]},
                {**base, "source_files": [{"path": str(SHELL_SCRIPT), "sha256": [], "mode": True}]},
                {**base, "managed_block": None},
                {**base, "profile_path": []},
            ]
            for raw in variants:
                with self.subTest(raw=raw):
                    path.write_text(json.dumps(raw), encoding="utf-8")
                    with self.assertRaises(ShellIntegrationError):
                        load_shell_plan(path)
            self.assertFalse((home / ".bashrc").exists())
            self.assertFalse((home / ".byte-backups").exists())

    def test_shell_asset_is_posix_and_idempotent_when_sourced_twice(self) -> None:
        syntax = subprocess.run(
            ["sh", "-n", str(SHELL_SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        command = (
            f". '{SHELL_SCRIPT}'; . '{SHELL_SCRIPT}'; "
            "byte_status; printf '%s\\n' \"$BYTE_CORE_SHELL_LOADED\""
        )
        completed = subprocess.run(
            ["bash", "-c", command],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "Byte shell integration is active.\n1\n",
        )

    @unittest.skipUnless(shutil.which("zsh"), "zsh is optional")
    def test_shell_asset_sources_twice_in_zsh(self) -> None:
        completed = subprocess.run(
            [
                "zsh", "-c",
                f". '{SHELL_SCRIPT}'; . '{SHELL_SCRIPT}'; byte_status",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout, "Byte shell integration is active.\n"
        )


if __name__ == "__main__":
    unittest.main()
