"""Release evidence targets and informational, read-only operating-system detection."""

from __future__ import annotations

from collections.abc import Mapping
import platform
import re

# Required native release observations, separate from runtime prerequisites.
RELEASE_TARGETS = frozenset({
    ("kubuntu-26.04", "x86_64"),
    ("macos-26", "arm64"),
})
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


def _identifier(value: object) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        return "unknown"
    return value


def linux_release(release: Mapping[str, object]) -> str:
    """Classify explicit OS metadata without inferring a desktop variant."""
    if not isinstance(release, Mapping):
        return "unknown"
    identifier = _identifier(release.get("ID"))
    version = _identifier(release.get("VERSION_ID"))
    if "unknown" in {identifier, version}:
        return "unknown"
    if identifier == "ubuntu" and release.get("VARIANT_ID") == "kubuntu":
        return f"kubuntu/{version}"
    return f"{identifier}/{version}"


def host_release(system: str) -> str:
    """Detect an informational release identity; never decide runtime readiness."""
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
    return linux_release(release)
