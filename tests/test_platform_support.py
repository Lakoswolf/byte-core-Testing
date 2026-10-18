from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from byte_core import platform_support as support


class PlatformSupportTests(unittest.TestCase):
    def test_release_targets_are_independent_evidence_requirements(self):
        self.assertEqual(support.RELEASE_TARGETS, {
            ("kubuntu-26.04", "x86_64"), ("macos-26", "arm64"),
        })

    def test_explicit_release_and_variant_metadata(self):
        cases = (
            ({"ID": "kubuntu", "VERSION_ID": "26.04"}, "kubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": "kubuntu"}, "kubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.04"}, "ubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "24.04"}, "ubuntu/24.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.10", "VARIANT_ID": "kubuntu"}, "kubuntu/26.10"),
            ({"ID": "fedora", "VERSION_ID": "44"}, "fedora/44"),
        )
        for release, expected in cases:
            with self.subTest(release=release):
                self.assertEqual(support.linux_release(release), expected)

    def test_related_distribution_display_name_and_desktop_session_do_not_qualify(self):
        cases = (
            {"ID": "neon", "VERSION_ID": "26.04", "ID_LIKE": "ubuntu kubuntu"},
            {"ID": "debian", "VERSION_ID": "13", "VARIANT_ID": "kubuntu"},
            {"ID": "ubuntu", "VERSION_ID": "26.04", "NAME": "Kubuntu", "PRETTY_NAME": "Kubuntu 26.04", "VARIANT": "Kubuntu"},
        )
        for release in cases:
            with self.subTest(release=release), mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "KDE", "DESKTOP_SESSION": "plasma"}):
                self.assertEqual(support.linux_release(release), f"{release['ID']}/{release['VERSION_ID']}")

    def test_conflicting_or_malformed_variant_does_not_infer_kubuntu(self):
        for variant in ("ubuntu", "server", "Kubuntu", "", None, False, [], "kubuntu\n", "$(fictional)"):
            with self.subTest(variant=variant):
                self.assertEqual(support.linux_release(
                    {"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": variant}),
                    "ubuntu/26.04")

    def test_missing_malformed_and_unbounded_release_fields_are_unknown(self):
        for release in (None, [], "ubuntu", {}, {"ID": "ubuntu"}, {"VERSION_ID": "26.04"}):
            with self.subTest(release=release):
                self.assertEqual(support.linux_release(release), "unknown")
        for bad in (None, False, 26.04, [], {}, "Ubuntu", " ubuntu", "ubuntu ", "26.04\n", "x" * 65, "$(fictional)", "26/04"):
            for key in ("ID", "VERSION_ID"):
                release = {"ID": "ubuntu", "VERSION_ID": "26.04", key: bad}
                with self.subTest(key=key, bad=bad):
                    self.assertEqual(support.linux_release(release), "unknown")

    def test_linux_identity_uses_only_os_metadata_without_applications(self):
        for release, expected in (
            ({"ID": "ubuntu", "VERSION_ID": "26.04"}, "ubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": "kubuntu"}, "kubuntu/26.04"),
            ({}, "unknown"), (None, "unknown"),
        ):
            with (
                self.subTest(release=release),
                mock.patch.object(support.platform, "freedesktop_os_release", return_value=release),
                mock.patch("subprocess.run", side_effect=AssertionError("application launch forbidden")),
                mock.patch("subprocess.Popen", side_effect=AssertionError("application launch forbidden")),
            ):
                self.assertEqual(support.host_release("Linux"), expected)

    def test_unavailable_or_malformed_os_release_degrades_to_unknown(self):
        for error in (OSError(), ValueError(), UnicodeError()):
            with self.subTest(error=error), mock.patch.object(support.platform, "freedesktop_os_release", side_effect=error):
                self.assertEqual(support.host_release("Linux"), "unknown")

    def test_macos_major_version_detection_is_preserved(self):
        for version, expected in (("15.7.1", "macos/15"), ("26.4.0", "macos/26"), ("27.0", "macos/27"), ("", "unknown"), (None, "unknown"), ("26\n", "unknown")):
            with self.subTest(version=version), mock.patch.object(support.platform, "mac_ver", return_value=(version, (), "")):
                self.assertEqual(support.host_release("Darwin"), expected)
        self.assertEqual(support.host_release("FictionOS"), "unknown")


if __name__ == "__main__":
    unittest.main()
