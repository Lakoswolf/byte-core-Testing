"""Exact release targets and conservative, read-only operating-system detection."""

from __future__ import annotations

from collections.abc import Mapping
import platform
import re
import subprocess

SUPPORTED_HOSTS = frozenset(
    {
        ("linux", "x86_64", "ubuntu/24.04"),
        ("linux", "x86_64", "kubuntu/26.04"),
        ("macos", "arm64", "macos/15"),
        ("macos", "arm64", "macos/26"),
    }
)
# The release gate and runtime share one exact set of OS/architecture targets.
RELEASE_TARGETS = frozenset(
    (release.replace("/", "-"), architecture)
    for _system, architecture, release in SUPPORTED_HOSTS
)
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_PACKAGE_QUERY = (
    "/usr/bin/dpkg-query", "--admindir=/var/lib/dpkg", "--no-pager", "--show",
    "--showformat=${binary:Package}\t${Architecture}\t${Status}\\n",
    "kubuntu-desktop:amd64",
)
_PACKAGE_RECORDS = frozenset({
    b"kubuntu-desktop\tamd64\tinstall ok installed\n",
    b"kubuntu-desktop:amd64\tamd64\tinstall ok installed\n",
    b"kubuntu-desktop\tamd64\thold ok installed\n",
    b"kubuntu-desktop:amd64\tamd64\thold ok installed\n",
})


def _identifier(value: object) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        return "unknown"
    return value


def linux_release(
    release: Mapping[str, object], *, kubuntu_desktop_installed: bool = False,
) -> str:
    """Classify supplied facts without probing, shell expansion, or inference.

    Package evidence may refine Ubuntu 26.04 only when VARIANT_ID is absent.
    An explicit conflicting or malformed variant never becomes Kubuntu.
    """
    if not isinstance(release, Mapping):
        return "unknown"
    identifier = _identifier(release.get("ID"))
    version = _identifier(release.get("VERSION_ID"))
    if "unknown" in {identifier, version}:
        return "unknown"
    if identifier == "ubuntu" and version == "26.04":
        variant = release.get("VARIANT_ID")
        if variant == "kubuntu" or (
            "VARIANT_ID" not in release and kubuntu_desktop_installed is True
        ):
            return "kubuntu/26.04"
    return f"{identifier}/{version}"


def _kubuntu_desktop_installed() -> bool:
    """Query one local package, never install it or enumerate host inventory.

    The fixed system executable and database plus a minimal environment prevent
    PATH, alternate dpkg roots, pagers, or locale settings from selecting facts.
    The query is limited to one package and two seconds; only a <=1024-byte
    exact successful record counts as evidence. Raw output is never reported.
    """
    try:
        result = subprocess.run(
            list(_PACKAGE_QUERY), check=False,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "DPKG_NLS": "0"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (
        result.returncode == 0 and type(result.stdout) is bytes
        and len(result.stdout) <= 1024 and result.stdout in _PACKAGE_RECORDS
    )


def host_release(system: str) -> str:
    """Detect a release identity; support still requires its exact architecture."""
    if system == "Darwin":
        try:
            raw_version = platform.mac_ver()[0]
        except (OSError, ValueError, TypeError, IndexError):
            return "unknown"
        if type(raw_version) is not str:
            return "unknown"
        version = _identifier(raw_version.partition(".")[0])
        return "unknown" if version == "unknown" else f"macos/{version}"
    if system != "Linux":
        return "unknown"
    try:
        release = platform.freedesktop_os_release()
    except (OSError, ValueError, UnicodeError):
        return "unknown"
    if not isinstance(release, Mapping):
        return "unknown"
    installed = False
    if (release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "26.04"
            and "VARIANT_ID" not in release):
        installed = _kubuntu_desktop_installed()
    return linux_release(release, kubuntu_desktop_installed=installed)
