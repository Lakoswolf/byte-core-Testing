"""Exercise the shell bootstrap with fake package managers; never install packages."""
import os
from pathlib import Path
import pty
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'posix', 'POSIX bootstrap')
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bin = Path(self.temp.name)
        self.state = self.bin / 'installed'
        self.log = self.bin / 'calls'
        self.env = dict(os.environ, PATH=str(self.bin), FAKE_STATE=str(self.state),
                        FAKE_LOG=str(self.log))
        self.command('dirname', 'exec /usr/bin/dirname "$@"')
        self.command('uname', 'echo Linux')
        self.command('id', 'echo 1000')
        self.command('sudo', 'exec "$@"')
        self.command('python3', 'if [ "$1" = -c ]; then [ -f "$FAKE_STATE" ]; else printf "wizard:%s\\n" "$*"; fi')
        self.command('git', '[ -f "$FAKE_STATE" ]')
        self.command('apt-get', 'echo "$*" >> "$FAKE_LOG"; case "$*" in *install*) : > "$FAKE_STATE";; esac')

    def command(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o700)

    def run_bootstrap(self, *args, approval=None):
        master = slave = None
        if approval is not None:
            master, slave = pty.openpty()
        try:
            process = subprocess.Popen(['/bin/sh', str(ROOT / 'scripts/setup_byte_core.sh'), *args],
                                       env=self.env, stdin=slave if slave is not None else subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if master is not None:
                os.write(master, (approval + '\n').encode())
            output, _ = process.communicate(timeout=10)
            return process.returncode, output
        finally:
            if master is not None:
                os.close(master)
                os.close(slave)

    def test_ready_handoff_preserves_arguments_without_install(self):
        self.state.touch()
        status, output = self.run_bootstrap('--core-root', '/fictional/path with spaces')
        self.assertEqual(status, 0, output)
        self.assertIn('/fictional/path with spaces', output)
        self.assertFalse(self.log.exists())

    def test_noninteractive_and_preview_never_install(self):
        for args in [(), ('--plan-only',), ('--help',)]:
            status, output = self.run_bootstrap(*args)
            self.assertEqual(status, 3, output)
        self.assertFalse(self.log.exists())

    def test_decline_never_installs(self):
        status, output = self.run_bootstrap(approval='no')
        self.assertEqual(status, 5, output)
        self.assertFalse(self.log.exists())

    def test_git_only_install_for_download(self):
        self.command('python3', 'if [ "$1" = -c ]; then exit 0; else echo wizard; fi')
        status, output = self.run_bootstrap('--from-repo', approval='yes')
        self.assertEqual(status, 0, output)
        self.assertEqual(self.log.read_text(), 'update\n--no-remove install git\n')

    def test_manager_failure_stops_before_wizard(self):
        self.command('apt-get', 'exit 1')
        status, output = self.run_bootstrap(approval='yes')
        self.assertEqual(status, 3, output)
        self.assertNotIn('wizard:', output)

    def test_homebrew_installs_and_rechecks_python(self):
        self.command('uname', 'echo Darwin')
        self.command('brew', 'case "$1" in install) echo "$*" >> "$FAKE_LOG"; : > "$FAKE_STATE";; --prefix) echo /fictional/python;; esac')
        status, output = self.run_bootstrap(approval='yes')
        self.assertEqual(status, 0, output)
        self.assertEqual(self.log.read_text(), 'install python@3.13\n')

    def test_unsatisfied_install_stops(self):
        self.command('uname', 'echo Darwin')
        self.command('brew', 'case "$1" in --prefix) echo /fictional/python;; esac')
        status, output = self.run_bootstrap(approval='yes')
        self.assertEqual(status, 3, output)
        self.assertNotIn('wizard:', output)

    def test_preview_with_terminal_still_never_installs(self):
        status, output = self.run_bootstrap('--plan-only', approval='yes')
        self.assertEqual(status, 3, output)
        self.assertFalse(self.log.exists())

    def test_missing_package_manager_explains_manual_path(self):
        self.command('uname', 'echo Darwin')
        status, output = self.run_bootstrap(approval='yes')
        self.assertEqual(status, 3, output)
        self.assertIn('Install Python 3.11+', output)
        self.assertFalse(self.log.exists())
