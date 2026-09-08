"""Explicit, data-only configuration for experimental shell helpers."""

from __future__ import annotations

import copy
from pathlib import Path
import re
import tomllib

from .inventory_io import InventoryError, read_bytes


class HelperConfigError(ValueError):
    """Configuration failure without deployment values in its message."""


DEFAULTS = {
    "schema_version": 1,
    "shell": {
        "prompt_label": "Byte", "prompt_color": "none",
        "prompt_directory": True, "prompt_git": True,
        "aliases": False, "prompt": False, "history": False,
        "highlighting": False,
    },
    "assistant": {},
    "repositories": [],
    "devices": [],
    "network": {"ping_timeout": 2, "workers": 4, "relay_timeout": 10},
}

_SHELL_STRINGS = {
    "development_directory", "prompt_label", "prompt_color", "highlighting_file",
    "highlighting_command_style", "highlighting_unknown_style", "highlighting_path_style",
}
_SHELL_BOOLS = {"prompt_directory", "prompt_git", "aliases", "prompt", "history", "highlighting"}


def _fail(key: str) -> None:
    # Keys passed here are fixed schema names, never untrusted values.
    raise HelperConfigError(f"invalid helper setting: {key}")


def _table(value: object, allowed: set[str], key: str) -> dict:
    if type(value) is not dict or set(value) - allowed:
        _fail(key)
    return value


def _text(value: object, key: str, *, limit: int = 4096, empty: bool = False) -> str:
    if (type(value) is not str or len(value) > limit
            or (not empty and not value.strip())
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        _fail(key)
    return value


def _path(value: object, key: str) -> str:
    value = _text(value, key)
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        _fail(key)
    return value


def _argv(value: object, key: str, *, nonempty: bool = False) -> list[str]:
    if type(value) is not list or len(value) > 64 or (nonempty and not value):
        _fail(key)
    for item in value:
        _text(item, key, empty=True)
    return value


def _items(value: object, key: str) -> list[dict]:
    if type(value) is not list or len(value) > 64:
        _fail(key)
    names = set()
    for item in value:
        if type(item) is not dict:
            _fail(key)
        name = _text(item.get("name"), f"{key}.name", limit=80)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name in names:
            _fail(f"{key}.name")
        names.add(name)
    return value


def validate(document: object) -> dict:
    """Return a fresh normalized configuration; never execute or discover data."""
    data = _table(document, set(DEFAULTS), "root")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        _fail("schema_version")
    shell = _table(data.get("shell", {}), _SHELL_STRINGS | _SHELL_BOOLS, "shell")
    for key, value in shell.items():
        if key in _SHELL_BOOLS:
            if type(value) is not bool:
                _fail(f"shell.{key}")
        elif key in {"development_directory", "highlighting_file"}:
            _path(value, f"shell.{key}")
        else:
            _text(value, f"shell.{key}", limit=128, empty=key.endswith("_style"))
    if shell.get("prompt_color", "none") not in {"none", "cyan", "green", "yellow"}:
        _fail("shell.prompt_color")
    if shell.get("highlighting") and not shell.get("highlighting_file"):
        _fail("shell.highlighting_file (required when highlighting is enabled)")
    assistant = _table(data.get("assistant", {}), {"executable", "new_args", "resume_args"}, "assistant")
    if "executable" in assistant:
        executable = _text(assistant["executable"], "assistant.executable")
        if executable.startswith("-"):
            _fail("assistant.executable")
        if "/" in executable:
            _path(executable, "assistant.executable")
    for key in ("new_args", "resume_args"):
        if key in assistant:
            _argv(assistant[key], f"assistant.{key}")
    repositories = _items(data.get("repositories", []), "repositories")
    for repo in repositories:
        _table(repo, {"name", "path", "remote", "branch"}, "repositories")
        _path(repo.get("path"), "repositories.path")
        for key in ("remote", "branch"):
            value = _text(repo.get(key), f"repositories.{key}", limit=256)
            if value.startswith("-"):
                _fail(f"repositories.{key}")
    _items(data.get("devices", []), "devices")
    # Share the pure operational validator so validation and planning agree.
    from .helper_network import NetworkHelperError, validate_settings
    try:
        network_settings = validate_settings(data)
    except NetworkHelperError as error:
        raise HelperConfigError(str(error)) from None
    result = copy.deepcopy(DEFAULTS)
    for key in ("shell", "assistant", "network"):
        result[key].update(copy.deepcopy(data.get(key, {})))
    for key in ("repositories", "devices"):
        result[key] = copy.deepcopy(data.get(key, []))
    result.update(network_settings)
    return result


def load(path: str | None = None) -> dict:
    """Load only the explicitly selected standalone helper file, or defaults."""
    if path is None:
        return copy.deepcopy(DEFAULTS)
    try:
        document = tomllib.loads(read_bytes(path).decode("utf-8"))
    except (InventoryError, UnicodeError, tomllib.TOMLDecodeError):
        raise HelperConfigError("cannot read helpers config: use an absolute regular TOML file without symlinks") from None
    return validate(document)


def get_scalar(config: dict, key: str) -> str:
    # Only these scalar settings are exposed to the sourced shell.
    if key not in {f"shell.{name}" for name in _SHELL_STRINGS | _SHELL_BOOLS}:
        raise HelperConfigError("unknown scalar helper setting")
    name = key.split(".", 1)[1]
    if name not in config["shell"]:
        raise HelperConfigError(f"configure {key} in the selected helpers TOML file")
    value = config["shell"][name]
    return str(value).lower() if type(value) is bool else value
