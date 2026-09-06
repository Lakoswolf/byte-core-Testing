from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from byte_core import platform_support as support


class PlatformSupportTests(unittest.TestCase):
    def test_release_targets_match_runtime_targets_exactly(self):
        self.assertEqual(support.RELEASE_TARGETS, {
            ("ubuntu-24.04", "x86_64"), ("kubuntu-26.04", "x86_64"),
            ("macos-15", "arm64"), ("macos-26", "arm64"),
        })
        self.assertNotIn(("linux", "x86_64", "ubuntu/26.04"), support.SUPPORTED_HOSTS)
        self.assertNotIn(("linux", "arm64", "kubuntu/26.04"), support.SUPPORTED_HOSTS)

    def test_explicit_kubuntu_identification_and_package_fallback(self):
        cases = (
            ({"ID": "kubuntu", "VERSION_ID": "26.04"}, False, "kubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": "kubuntu"}, False, "kubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.04"}, True, "kubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.04"}, False, "ubuntu/26.04"),
            ({"ID": "ubuntu", "VERSION_ID": "24.04"}, True, "ubuntu/24.04"),
            ({"ID": "kubuntu", "VERSION_ID": "24.04"}, True, "kubuntu/24.04"),
            ({"ID": "ubuntu", "VERSION_ID": "26.10"}, True, "ubuntu/26.10"),
        )
        for release, installed, expected in cases:
            with self.subTest(release=release, installed=installed):
                self.assertEqual(support.linux_release(release, kubuntu_desktop_installed=installed), expected)

    def test_related_distribution_display_name_and_desktop_session_do_not_qualify(self):
        cases = (
            {"ID": "neon", "VERSION_ID": "26.04", "ID_LIKE": "ubuntu kubuntu"},
            {"ID": "debian", "VERSION_ID": "13", "VARIANT_ID": "kubuntu"},
            {"ID": "ubuntu", "VERSION_ID": "26.04", "NAME": "Kubuntu", "PRETTY_NAME": "Kubuntu 26.04", "VARIANT": "Kubuntu"},
        )
        for release in cases:
            with self.subTest(release=release), mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "KDE", "DESKTOP_SESSION": "plasma"}):
                self.assertEqual(support.linux_release(release), f"{release['ID']}/{release['VERSION_ID']}")
        self.assertEqual(support.linux_release(cases[0], kubuntu_desktop_installed=True), "neon/26.04")

    def test_conflicting_or_malformed_variant_blocks_package_fallback(self):
        for variant in ("ubuntu", "server", "Kubuntu", "", None, False, [], "kubuntu\n", "$(fictional)"):
            with self.subTest(variant=variant):
                self.assertEqual(support.linux_release(
                    {"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": variant},
                    kubuntu_desktop_installed=True), "ubuntu/26.04")
        self.assertEqual(support.linux_release(
            {"ID": "ubuntu", "VERSION_ID": "26.04"}, kubuntu_desktop_installed=1), "ubuntu/26.04")

    def test_missing_malformed_and_unbounded_release_fields_are_unknown(self):
        for release in (None, [], "ubuntu", {}, {"ID": "ubuntu"}, {"VERSION_ID": "26.04"}):
            with self.subTest(release=release):
                self.assertEqual(support.linux_release(release), "unknown")
        for bad in (None, False, 26.04, [], {}, "Ubuntu", " ubuntu", "ubuntu ", "26.04\n", "x" * 65, "$(fictional)", "26/04"):
            for key in ("ID", "VERSION_ID"):
                release = {"ID": "ubuntu", "VERSION_ID": "26.04", key: bad}
                with self.subTest(key=key, bad=bad):
                    self.assertEqual(support.linux_release(release), "unknown")

    def test_host_probes_one_package_only_for_ambiguous_ubuntu_2604(self):
        with (
            mock.patch.object(support.platform, "freedesktop_os_release", return_value={"ID": "ubuntu", "VERSION_ID": "26.04"}),
            mock.patch.object(support, "_kubuntu_desktop_installed", return_value=True) as probe,
        ):
            self.assertEqual(support.host_release("Linux"), "kubuntu/26.04")
            probe.assert_called_once_with()
        for release in (
            {"ID": "ubuntu", "VERSION_ID": "24.04"},
            {"ID": "kubuntu", "VERSION_ID": "26.04"},
            {"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": "kubuntu"},
            {"ID": "ubuntu", "VERSION_ID": "26.04", "VARIANT_ID": "server"},
            {"ID": "neon", "VERSION_ID": "26.04"},
            {}, None,
        ):
            with self.subTest(release=release), mock.patch.object(support.platform, "freedesktop_os_release", return_value=release), mock.patch.object(support, "_kubuntu_desktop_installed") as probe:
                support.host_release("Linux")
                probe.assert_not_called()

    def test_package_query_is_fixed_read_only_bounded_and_environment_independent(self):
        result = subprocess.CompletedProcess([], 0, b"kubuntu-desktop\tamd64\tinstall ok installed\n")
        with mock.patch.object(support.subprocess, "run", return_value=result) as run:
            self.assertTrue(support._kubuntu_desktop_installed())
        run.assert_called_once_with(
            ["/usr/bin/dpkg-query", "--admindir=/var/lib/dpkg", "--no-pager", "--show",
             "--showformat=${binary:Package}\t${Architecture}\t${Status}\\n", "kubuntu-desktop:amd64"],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=2, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "DPKG_NLS": "0"},
        )

    def test_installed_and_held_package_records_are_accepted(self):
        for name in ("kubuntu-desktop", "kubuntu-desktop:amd64"):
            for selected in ("install", "hold"):
                output = f"{name}\tamd64\t{selected} ok installed\n".encode()
                with self.subTest(name=name, selected=selected), mock.patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output)):
                    self.assertTrue(support._kubuntu_desktop_installed())

    def test_malformed_absent_unconfigured_and_wrong_package_records_are_rejected(self):
        valid = b"kubuntu-desktop\tamd64\tinstall ok installed\n"
        cases = (
            (1, valid), (0, b""), (0, valid + valid), (0, valid + b"unexpected\n"),
            (0, valid.rstrip()), (0, valid.replace(b"amd64", b"arm64")),
            (0, valid.replace(b"kubuntu-desktop", b"ubuntu-desktop")),
            (0, valid.replace(b"install ok installed", b"install ok unpacked")),
            (0, valid.replace(b"install ok installed", b"install ok half-configured")),
            (0, valid.replace(b"install ok installed", b"deinstall ok config-files")),
            (0, valid.replace(b"install ok installed", b"install reinstreq installed")),
            (0, b"x" * 1025), (0, valid.decode()), (0, None),
        )
        for code, output in cases:
            with self.subTest(code=code, output=output), mock.patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], code, output)):
                self.assertFalse(support._kubuntu_desktop_installed())

    def test_missing_or_timed_out_query_leaves_plain_ubuntu_unsupported(self):
        for error in (FileNotFoundError(), PermissionError(), subprocess.TimeoutExpired("fictional-query", 2)):
            with self.subTest(error=error), mock.patch.object(support.subprocess, "run", side_effect=error), mock.patch.object(support.platform, "freedesktop_os_release", return_value={"ID": "ubuntu", "VERSION_ID": "26.04"}):
                self.assertEqual(support.host_release("Linux"), "ubuntu/26.04")

    def test_unavailable_or_malformed_os_release_degrades_to_unknown(self):
        for error in (OSError(), ValueError(), UnicodeError()):
            with self.subTest(error=error), mock.patch.object(support.platform, "freedesktop_os_release", side_effect=error):
                self.assertEqual(support.host_release("Linux"), "unknown")

    def test_macos_major_version_detection_is_preserved(self):
        for version, expected in (("15.7.1", "macos/15"), ("26.4.0", "macos/26"), ("27.0", "macos/27"), ("", "unknown"), (None, "unknown"), ("26\n", "unknown")):
            with self.subTest(version=version), mock.patch.object(support.platform, "mac_ver", return_value=(version, (), "")), mock.patch.object(support, "_kubuntu_desktop_installed") as probe:
                self.assertEqual(support.host_release("Darwin"), expected)
                probe.assert_not_called()
        self.assertEqual(support.host_release("FictionOS"), "unknown")


if __name__ == "__main__":
    unittest.main()
