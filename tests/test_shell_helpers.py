from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from byte_core import helper_shell

ASSET = ROOT / "shell" / "byte-shell.sh"


class ShellHelpersTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name).resolve()
        self.config = self.work / "helpers.toml"
        self.config.write_text("schema_version = 1\n")
        python3 = shutil.which("python3") or sys.executable
        self.env = {
            "HOME": str(self.work), "PATH": str(Path(python3).parent) + os.pathsep + os.defpath, "TERM": "dumb",
            "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "BYTE_CORE_HELPERS_CONFIG": str(self.config),
        }

    def shell(self, body, *, shell="bash", interactive=False, extra_env=None):
        executable = shutil.which(shell)
        if executable is None:
            self.skipTest(f"{shell} unavailable")
        flags = ["--noprofile", "--norc"] if shell == "bash" else ["-f"] if shell == "zsh" else []
        command = [executable, *flags, "-ic" if interactive else "-c", '. "$1"\n' + body, "fixture", str(ASSET)]
        return subprocess.run(command, env={**self.env, **(extra_env or {})}, cwd=self.work,
                              text=True, capture_output=True, timeout=20)

    def git(self, *arguments, cwd=None):
        return subprocess.run(["git", *arguments], cwd=cwd or self.work, env=self.env,
                              text=True, capture_output=True, check=True)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_basic_posix_source_and_inherited_loaded_flag(self):
        result = self.shell('byte_status; bytehelp; byte_status', shell="sh",
                            extra_env={"BYTE_CORE_SHELL_LOADED": "1"})
        self.assert_success(result)
        self.assertEqual(result.stdout.count("Byte shell integration is active."), 2)

    def test_invalid_repository_does_not_change_directory(self):
        ordinary = self.work / "ordinary"
        ordinary.mkdir()
        self.git("init", "--bare", str(self.work / "bare"))
        result = self.shell('before=$PWD; byte_repo ordinary; a=$?; test "$a" -ne 0 && test "$PWD" = "$before" && byte_repo bare; b=$?; test "$b" -ne 0 && test "$PWD" = "$before"')
        self.assert_success(result)

    def test_repo_navigation_handles_spaces_and_cdpath(self):
        self.git("init", str(self.work / "fictional project"))
        for shell in ("bash", "zsh", "sh"):
            with self.subTest(shell=shell):
                result = self.shell('CDPATH=/does-not-exist; byte_repo "fictional project"; test "${PWD##*/}" = "fictional project"', shell=shell)
                self.assert_success(result)

    def test_dev_requires_setting_and_uses_absolute_literal_path(self):
        result = self.shell('before=$PWD; dev; code=$?; test "$code" -ne 0 && test "$PWD" = "$before"')
        self.assert_success(result)
        destination = self.work / "fictional development"
        destination.mkdir()
        self.config.write_text('schema_version=1\n[shell]\ndevelopment_directory=' + json.dumps(str(destination)) + '\n')
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                result = self.shell('dev; test "${PWD##*/}" = "fictional development"', shell=shell)
                self.assert_success(result)

    def test_wrappers_forward_argument_boundaries(self):
        result = self.shell('_byte_helpers() { printf "<%s>" "$@"; }; byten "two words"; byter --flag; bytegit --short; labstatus plan --device fictional; canisync plan; wakelan plan --device fictional')
        self.assert_success(result)
        self.assertEqual(result.stdout, '<assistant><new><--><two words><assistant><resume><--><--flag><git-status><--><--short><labstatus><plan><--device><fictional><canisync><plan><wakelan><plan><--device><fictional>')

    def test_noninteractive_features_are_not_enabled_by_config(self):
        self.config.write_text('schema_version=1\n[shell]\nprompt=true\nhistory=true\naliases=true\n')
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                result = self.shell('byteprompt status; bytehistory status; bytealiases status', shell=shell)
                self.assert_success(result)
                self.assertEqual(result.stdout.count(": off"), 3)

    def test_prompt_restoration_reload_and_literal_label(self):
        marker = self.work / "must-not-exist"
        label = f'$(touch {marker}) %F{{red}}'
        self.config.write_text('schema_version=1\n[shell]\nprompt_label=' + json.dumps(label) + '\nprompt_color="cyan"\nprompt_directory=false\nprompt_git=false\n')
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                rendering = ('if ( : "${PS1@P}" ) 2>/dev/null; then printf "%s\\n" "${PS1@P}"; else _byte_prompt_render; fi'
                             if shell == "bash" else 'print -P -- "$PS1"')
                result = self.shell('PS1="original prompt > "; byteprompt on; ' + rendering + '; rebyte; byteprompt status; byteprompt off; test "$PS1" = "original prompt > "', shell=shell, interactive=True)
                self.assert_success(result)
                self.assertIn("Byte prompt: on", result.stdout)
                self.assertFalse(marker.exists())

    def test_prompt_option_restoration(self):
        for shell, before, after in (
            ("bash", "shopt -u promptvars", "! shopt -q promptvars"),
            ("zsh", "unsetopt promptsubst promptpercent", 'test "$options[promptsubst]" = off && test "$options[promptpercent]" = off'),
        ):
            with self.subTest(shell=shell):
                result = self.shell(f'{before}; byteprompt on; byteprompt off; {after}', shell=shell, interactive=True)
                self.assert_success(result)

    def test_reload_keeps_disabled_preference_and_child_initializes(self):
        self.config.write_text('schema_version=1\n[shell]\nprompt=true\n')
        result = self.shell('byteprompt status; byteprompt off; rebyte; byteprompt status; export BYTE_CORE_SHELL_LOADED _BYTE_CORE_PID _BYTE_PROMPT; bash --noprofile --norc -ic \'. "$1"; byteprompt status\' fixture "$1"', interactive=True)
        self.assert_success(result)
        self.assertEqual(result.stdout.splitlines(), ['Byte prompt: on', 'Byte prompt: off', 'Byte prompt: on'])

    def test_aliases_preserve_existing_and_subsequent_definitions(self):
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                result = self.shell('alias ll="printf original"; bytealiases on; original=$(alias ll); alias la="printf later"; bytealiases off; test "$(alias ll)" = "$original" && alias la && ! alias ..', shell=shell, interactive=True)
                self.assert_success(result)
                self.assertIn("printf later", result.stdout)

    def test_bash_history_restores_bindings_and_macros(self):
        result = self.shell('bind -m emacs-standard \'"\\e[A": beginning-of-line\'; bind -m vi-insertion \'"\\e[B": "literal macro"\'; before=$(bind -m emacs-standard -p; bind -m vi-insertion -s); bytehistory on; rebyte; bytehistory off; after=$(bind -m emacs-standard -p; bind -m vi-insertion -s); test "$before" = "$after"', interactive=True)
        self.assert_success(result)

    def test_bash_history_preserves_arrow_shell_command_bindings(self):
        result = self.shell('bind -m emacs-standard -x \'"\\e[A": "printf fictional"\'; before=$(bind -m emacs-standard -X); bytehistory on; code=$?; after=$(bind -m emacs-standard -X); test "$code" -ne 0 && test "$before" = "$after"', interactive=True)
        self.assert_success(result)

    def test_zsh_history_restores_bindings(self):
        result = self.shell('bindkey -M emacs "^[[A" beginning-of-line; before=$(bindkey -M emacs; bindkey -M viins); bytehistory on; rebyte; bytehistory off; after=$(bindkey -M emacs; bindkey -M viins); test "$before" = "$after"', shell="zsh", interactive=True)
        self.assert_success(result)

    def test_zsh_history_refuses_existing_macro_without_changes(self):
        result = self.shell('bindkey -M emacs -s "^[[A" "literal macro"; before=$(bindkey -M emacs); bytehistory on; code=$?; after=$(bindkey -M emacs); test "$code" -ne 0 && test "$before" = "$after"', shell="zsh", interactive=True)
        self.assert_success(result)

    def test_highlighting_is_explicit_once_and_reports_incomplete_reversal(self):
        plugin = self.work / "fictional-highlighting.zsh"
        plugin.write_text('typeset -gA ZSH_HIGHLIGHT_STYLES\nBYTE_FICTIONAL_HIGHLIGHT_COUNT=$(( ${BYTE_FICTIONAL_HIGHLIGHT_COUNT:-0} + 1 ))\n')
        self.config.write_text('schema_version=1\n[shell]\nhighlighting_file=' + json.dumps(str(plugin)) + '\nhighlighting_command_style="fg=green"\n')
        result = self.shell('test "${BYTE_FICTIONAL_HIGHLIGHT_COUNT:-0}" = 0; bytehighlight on; rebyte; bytehighlight on; test "$BYTE_FICTIONAL_HIGHLIGHT_COUNT" = 1 && test "$ZSH_HIGHLIGHT_STYLES[command]" = fg=green || exit 9; bytehighlight off; test "$?" -ne 0; bytehighlight status', shell="zsh", interactive=True)
        self.assert_success(result)
        self.assertIn("restart", result.stderr.lower())
        self.assertIn("Byte highlighting: on", result.stdout)

    def test_config_is_not_sourced_and_invalid_config_preserves_helpers(self):
        marker = self.work / "must-not-exist"
        self.config.write_text(f'touch {marker}\n')
        result = self.shell('byte_status; byteprompt status', interactive=True)
        self.assert_success(result)
        self.assertFalse(marker.exists())
        self.assertIn("Byte prompt: off", result.stdout)

    def test_partial_highlighting_failure_is_not_replayed(self):
        plugin = self.work / "fictional-failing-highlighting.zsh"
        plugin.write_text('BYTE_FICTIONAL_HIGHLIGHT_COUNT=$(( ${BYTE_FICTIONAL_HIGHLIGHT_COUNT:-0} + 1 ))\nreturn 1\n')
        self.config.write_text('schema_version=1\n[shell]\nhighlighting_file=' + json.dumps(str(plugin)) + '\n')
        result = self.shell('bytehighlight on; first=$?; rebyte; bytehighlight on; second=$?; test "$first" -ne 0 && test "$second" -ne 0 && test "$BYTE_FICTIONAL_HIGHLIGHT_COUNT" = 1; bytehighlight status', shell="zsh", interactive=True)
        self.assert_success(result)
        self.assertIn("Byte highlighting: partial", result.stdout)

    def test_assistant_argv_is_literal_and_runs_once_at_project_root(self):
        project = self.work / "fictional project"
        project.mkdir()
        self.git("init", str(project))
        subdirectory = project / "nested"
        subdirectory.mkdir()
        app = self.work / "fictional-assistant"
        output = self.work / "invocation.json"
        app.write_text('#!/usr/bin/python3\nimport json, os, pathlib, sys\npathlib.Path(sys.argv[1]).write_text(json.dumps({"args":sys.argv[2:], "cwd":os.getcwd()}))\nsys.exit(7)\n')
        app.chmod(0o700)
        self.config.write_text('schema_version=1\n[assistant]\nexecutable=' + json.dumps(str(app)) + '\nnew_args=' + json.dumps([str(output), "--project={project}", "$(false)", "two words"]) + '\nresume_args=[]\n')
        result = self.shell('cd "fictional project/nested"; byten "literal; argument"')
        self.assertEqual(result.returncode, 7, result.stderr)
        observed = json.loads(output.read_text())
        self.assertEqual(observed, {"args": [f"--project={project}", "$(false)", "two words", "literal; argument"], "cwd": str(project)})

    def test_assistant_missing_settings_and_outside_git_are_errors(self):
        with self.assertRaises(helper_shell.ShellHelperError):
            helper_shell.run_assistant({}, "new", [])
        with mock.patch.object(helper_shell.shutil, "which", side_effect=AssertionError("do not resolve invalid paths")):
            with self.assertRaises(helper_shell.ShellHelperError):
                helper_shell.run_assistant({"assistant": {"executable": "/srv/../example", "new_args": []}}, "new", [])
        with mock.patch.object(helper_shell, "_git_project", side_effect=helper_shell.ShellHelperError("outside Git")):
            with self.assertRaises(helper_shell.ShellHelperError):
                helper_shell.run_assistant({"assistant": {"executable": "/usr/bin/true", "new_args": []}}, "new", [])

    def test_git_status_arguments_follow_fixed_subcommand(self):
        with mock.patch.object(helper_shell, "_git_project", return_value="/fictional/project"), mock.patch.object(helper_shell.subprocess, "run") as run:
            run.return_value.returncode = 3
            self.assertEqual(helper_shell.git_status(["--short", "--", "two words"]), 3)
            run.assert_called_once_with(["git", "status", "--short", "--", "two words"], check=False)

    def test_prompt_shows_dirty_branch_and_detached_revision(self):
        self.git("init")
        (self.work / "fictional.txt").write_text("example\n")
        self.git("add", "fictional.txt")
        self.git("-c", "user.name=Fictional", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Fictional fixture")
        branch = self.git("symbolic-ref", "--short", "HEAD").stdout.strip()
        result = self.shell('_byte_helpers prompt --shell bash')
        self.assert_success(result)
        self.assertIn(f"[{branch}*]", result.stdout)  # Helpers TOML remains untracked.
        self.git("checkout", "--detach")
        revision = self.git("rev-parse", "--short", "HEAD").stdout.strip()
        result = self.shell('_byte_helpers prompt --shell bash')
        self.assert_success(result)
        self.assertIn(f"[detached:{revision}*]", result.stdout)

    def test_prompt_omits_git_filters_and_partial_clone_without_execution(self):
        self.git("init")
        marker = self.work / "filter-ran"
        app = self.work / "fictional-filter"
        app.write_text('#!/usr/bin/python3\nimport pathlib, sys\npathlib.Path(' + repr(str(marker)) + ').touch()\nsys.stdout.write(sys.stdin.read())\n')
        app.chmod(0o700)
        (self.work / ".gitattributes").write_text("*.txt filter=fictional\n")
        tracked = self.work / "fictional.txt"
        tracked.write_text("example\n")
        self.git("add", ".gitattributes", "fictional.txt")
        self.git("config", "filter.fictional.clean", str(app))
        tracked.write_text("different example\n")
        result = self.shell('_byte_helpers prompt --shell bash')
        self.assert_success(result)
        self.assertNotIn("[", result.stdout)
        self.assertFalse(marker.exists())
        self.git("config", "--unset", "filter.fictional.clean")
        self.git("config", "remote.fictional.promisor", "true")
        result = self.shell('_byte_helpers prompt --shell bash')
        self.assert_success(result)
        self.assertNotIn("[", result.stdout)

    def test_prompt_sanitizes_control_characters_and_zsh_percent_data(self):
        with mock.patch.object(helper_shell.Path, "cwd", return_value=Path("/fictional/unsafe\x1b[31m%F{red}")):
            text = helper_shell.prompt_text({"shell": {"prompt_git": False}}, "zsh")
        self.assertNotIn("\x1b", text)
        self.assertIn("%%F{red}", text)

    def test_prompt_git_reader_enforces_output_and_time_bounds(self):
        fake_git = self.work / "git"
        fake_git.write_text('#!/usr/bin/python3\nimport sys\nsys.stdout.write("x" * (2 * 1024 * 1024 + 1))\n')
        fake_git.chmod(0o700)
        with mock.patch.dict(os.environ, {"PATH": str(self.work)}):
            self.assertIsNone(helper_shell._prompt_git(["status"], helper_shell.time.monotonic() + 2))
        fake_git.write_text('#!/usr/bin/python3\nimport time\ntime.sleep(5)\n')
        with mock.patch.dict(os.environ, {"PATH": str(self.work)}):
            start = helper_shell.time.monotonic()
            self.assertIsNone(helper_shell._prompt_git(["status"], start + 0.1))
            self.assertLess(helper_shell.time.monotonic() - start, 1)


if __name__ == "__main__":
    unittest.main()
