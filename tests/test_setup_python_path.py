"""Fictional fresh-shell and persistent Python selection checks."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import setup_byte_core as setup


class PythonPathTests(unittest.TestCase):
    def choice(self, answers, ready=False, preview=False):
        with mock.patch('builtins.input', side_effect=answers), \
                mock.patch.object(setup, 'fresh_python_check', return_value=ready) as check, \
                mock.patch.object(setup.shutil, 'which', return_value='/fictional/python/bin/python3'), \
                mock.patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                redirect_stdout(io.StringIO()):
            result = setup.python_path_choice('bash', '/fictional/home', plan_only=preview)
            return result, check.call_count

    def test_decline_does_not_execute_startup_files(self):
        self.assertEqual(self.choice(['n']), ((None, False), 0))

    def test_preview_does_not_execute_or_prompt(self):
        self.assertEqual(self.choice([], preview=True), ((None, False), 0))

    def test_ready_shell_needs_no_path_change(self):
        self.assertEqual(self.choice(['y'], ready=True), ((None, True), 1))

    def test_failed_check_offers_selection_or_manual_configuration(self):
        self.assertEqual(self.choice(['y', 'y'])[0], (Path('/fictional/python/bin'), True))
        self.assertEqual(self.choice(['y', 'n'])[0], (None, True))

    def test_session_reorders_python_without_duplicates_and_quotes_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            release = root / 'core'
            (release / 'shell').mkdir(parents=True)
            (release / 'shell/byte-shell.sh').write_text(':\n')
            python = root / "Python's bin"
            wrapper = root / 'session.sh'
            wrapper.write_text(setup.session_script(release, None, python))
            env = dict(os.environ, PATH=f'/old/bin:{python}:/usr/bin:{python}')
            result = subprocess.run(['/bin/sh', '-c', '. "$1"; . "$1"; printf "%s" "$PATH"',
                                     'fixture', str(wrapper)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            entries = result.stdout.split(':')
            self.assertEqual(entries.count(str(python)), 1)
            self.assertEqual(entries.count(str(release / 'bin')), 1)
            self.assertLess(entries.index(str(python)), entries.index('/old/bin'))
            self.assertEqual([x for x in entries if x not in {str(python), str(release / 'bin')}], ['/old/bin', '/usr/bin'])

    @unittest.skipUnless(shutil.which('bash'), 'Bash required')
    def test_fresh_check_uses_original_path_and_selected_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / '.bashrc').write_text('export PATH=' + setup.shlex.quote(str(Path(sys.executable).parent)) + ':"$PATH"\n')
            with mock.patch.dict(os.environ, {'BYTE_SETUP_ORIGINAL_PATH': '/nonexistent'}):
                self.assertTrue(setup.fresh_python_check('bash', str(root)))

    def test_reject_unsafe_path(self):
        for value in ['relative', '/bad:path', '/bad\npath']:
            with self.assertRaises(ValueError):
                setup.session_script(Path('/fictional/core'), None, Path(value))
