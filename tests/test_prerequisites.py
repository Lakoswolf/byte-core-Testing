from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from byte_core import prerequisites


class PrerequisiteTests(unittest.TestCase):
    def test_missing_directory_protection_only_blocks_guarded_io(self):
        with mock.patch.object(prerequisites.os, "O_NOFOLLOW", None):
            self.assertFalse(prerequisites.capabilities("setup")["guarded-io-api"])
            self.assertNotIn("guarded-io-api", prerequisites.capabilities("lifecycle"))
            self.assertEqual(prerequisites.capabilities("runtime"), {})

    def test_descriptor_and_no_follow_link_support_are_required(self):
        for capability in ("supports_dir_fd", "supports_follow_symlinks"):
            with self.subTest(capability=capability), mock.patch.object(prerequisites.os, capability, set()):
                self.assertFalse(prerequisites.capabilities("inventory")["guarded-io-api"])

    def test_missing_process_group_api_does_not_block_installation(self):
        with mock.patch.object(prerequisites.os, "killpg", None):
            self.assertFalse(prerequisites.capabilities("helpers")["process-api"])
            self.assertNotIn("process-api", prerequisites.capabilities("lifecycle"))

    def test_lifecycle_requires_no_follow_hardlinks_but_reporting_does_not(self):
        with mock.patch.object(prerequisites.os, "supports_follow_symlinks", set()):
            self.assertFalse(prerequisites.capabilities("lifecycle")["exclusive-publication-api"])
            self.assertNotIn("exclusive-publication-api", prerequisites.capabilities("reporting"))

    def test_missing_file_sync_is_reported_without_probing_filesystem(self):
        with mock.patch.object(prerequisites.os, "fsync", None), mock.patch.object(
            prerequisites.os, "open", side_effect=AssertionError("must not open files")
        ):
            self.assertFalse(prerequisites.capabilities("lifecycle")["filesystem-api"])


if __name__ == "__main__":
    unittest.main()
