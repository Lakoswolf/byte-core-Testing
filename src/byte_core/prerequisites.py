"""Read-only prerequisites for the implemented backends, never host allowlists.

API availability is a preflight, not a filesystem probe or release certification.
Operations retain their own target, executable, approval and verification checks.
"""

from __future__ import annotations

import os

FEATURES = (
    "runtime", "lifecycle", "inventory", "inventory-scan", "setup", "helpers",
    "shell-bash", "shell-zsh", "git", "reporting",
)
TOOLS = {"inventory-scan": "nmap", "shell-bash": "bash", "shell-zsh": "zsh"}


def capabilities(feature: str) -> dict[str, bool]:
    """Inspect Python's advertised APIs without writing files or running tools."""
    if feature not in FEATURES:
        raise ValueError("unknown prerequisite feature")
    if feature in {"runtime", "git"}:
        return {}
    result = {
        "filesystem-api": all(callable(getattr(os, name, None)) for name in (
            "open", "close", "fstat", "fsync", "replace", "chmod", "lstat",
        )),
    }
    if feature in {"lifecycle", "shell-bash", "shell-zsh"}:
        result["exclusive-publication-api"] = (
            callable(getattr(os, "link", None))
            and os.link in os.supports_follow_symlinks
        )
    if feature in {"inventory", "inventory-scan", "setup", "helpers"}:
        result["guarded-io-api"] = (
            all(isinstance(getattr(os, name, None), int) for name in (
                "O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK",
            ))
            and callable(getattr(os, "fchmod", None))
            and all(getattr(os, name, None) in os.supports_dir_fd
                    for name in ("open", "link", "unlink"))
            and os.link in os.supports_follow_symlinks
        )
    if feature == "helpers":
        result["process-api"] = all(callable(getattr(os, name, None)) for name in (
            "killpg", "setsid", "read",
        ))
    if feature == "inventory-scan":
        result["process-api"] = callable(getattr(os, "read", None))
    return result
