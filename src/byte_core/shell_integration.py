"""Exact, reversible Bash and Zsh profile integration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SHELL_PLAN_SCHEMA_VERSION = 2
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_PROFILE_BYTES = 1024 * 1024
MAX_PLAN_BYTES = 1024 * 1024
START_MARKER = "# >>> Byte Core managed shell integration >>>"
END_MARKER = "# <<< Byte Core managed shell integration <<<"
_DIGEST = re.compile(r"[0-9a-f]{64}")


class ShellIntegrationError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ShellSource:
    path: str
    sha256: str
    mode: int


@dataclass(frozen=True)
class ShellPlan:
    schema_version: int
    operation: str
    shell: str
    home_root: str
    profile_path: str
    shell_script_path: str
    syntax_highlighting_path: str | None
    original_exists: bool
    profile_mode: int
    original_sha256: str
    managed_block: str
    managed_block_sha256: str
    result_exists: bool
    result_sha256: str
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    backout: tuple[str, ...]
    plan_id: str
    source_files: tuple[ShellSource, ...] = ()


@dataclass(frozen=True)
class ShellResult:
    code: str
    plan_id: str
    profile_path: str
    backup_path: str


def build_shell_install_plan(
    home_root: str | os.PathLike[str],
    shell: str,
    shell_script_path: str | os.PathLike[str],
    syntax_highlighting_path: str | os.PathLike[str] | None = None,
) -> ShellPlan:
    home = _existing_directory(home_root, "invalid_home_root")
    profile = _profile_path(home, shell)
    script = _regular_file(shell_script_path, "invalid_shell_script")
    syntax = None
    if syntax_highlighting_path is not None:
        if shell != "zsh":
            raise ShellIntegrationError("syntax_highlighting_requires_zsh")
        syntax = _regular_file(
            syntax_highlighting_path, "invalid_syntax_highlighting"
        )
    original_exists, original, profile_mode = _profile_state(profile)
    _require_no_markers(original)
    separator = _profile_separator(original)
    block = _managed_block(
        script, syntax, len(separator), original_exists
    )
    result = original + separator + block.encode("utf-8")
    return _make_plan(
        "shell_install", shell, home, profile, script, syntax,
        original_exists, profile_mode, original, block, True, result,
        ("profile_unchanged", "managed_block_absent", "source_files_unchanged"),
        ("managed_block_exact", "unrelated_content_preserved", "source_files_unchanged"),
        ("restore_unchanged_profile_from_apply_backup",),
    )


def build_shell_removal_plan(
    home_root: str | os.PathLike[str],
    shell: str,
) -> ShellPlan:
    home = _existing_directory(home_root, "invalid_home_root")
    profile = _profile_path(home, shell)
    original_exists, original, profile_mode = _profile_state(profile)
    if not original_exists:
        raise ShellIntegrationError("managed_block_absent")
    block = _extract_block(original)
    script, syntax = _parse_managed_block(block, shell)
    result = _remove_block(original, block)
    result_exists = _block_original_exists(block) or bool(result)
    return _make_plan(
        "shell_remove", shell, home, profile, script, syntax,
        True, profile_mode, original, block, result_exists, result,
        ("profile_unchanged", "managed_block_exact"),
        ("managed_block_absent", "unrelated_content_preserved"),
        ("restore_unchanged_profile_from_remove_backup",),
    )


def load_shell_plan(path: str | os.PathLike[str]) -> ShellPlan:
    plan_path = _regular_file(path, "plan_read_error")
    try:
        raw = json.loads(_read_bounded(plan_path, MAX_PLAN_BYTES).decode("utf-8"))
    except ShellIntegrationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ShellIntegrationError("invalid_plan") from error
    keys = {
        "schema_version", "operation", "shell", "home_root", "profile_path",
        "shell_script_path", "syntax_highlighting_path", "original_exists",
        "profile_mode", "original_sha256", "managed_block",
        "managed_block_sha256", "result_exists",
        "result_sha256", "preconditions", "postconditions", "backout",
        "plan_id", "source_files",
    }
    if type(raw) is not dict or set(raw) != keys:
        raise ShellIntegrationError("invalid_plan")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != SHELL_PLAN_SCHEMA_VERSION:
        raise ShellIntegrationError("unsupported_plan")
    plan = ShellPlan(
        raw["schema_version"], raw["operation"], raw["shell"],
        raw["home_root"], raw["profile_path"], raw["shell_script_path"],
        raw["syntax_highlighting_path"], raw["original_exists"],
        raw["profile_mode"], raw["original_sha256"], raw["managed_block"],
        raw["managed_block_sha256"], raw["result_exists"],
        raw["result_sha256"],
        _string_tuple(raw["preconditions"]),
        _string_tuple(raw["postconditions"]),
        _string_tuple(raw["backout"]), raw["plan_id"],
        _source_tuple(raw["source_files"]),
    )
    _validate_plan(plan)
    return plan


def apply_shell_plan(plan: ShellPlan) -> ShellResult:
    _validate_plan(plan)
    profile = Path(plan.profile_path)
    _verify_sources(plan)
    exists, original, mode = _profile_state(profile)
    if (
        exists == plan.result_exists
        and (not exists or mode == plan.profile_mode)
        and _digest(original) == plan.result_sha256
        and (
            (plan.operation == "shell_install"
             and plan.managed_block.encode("utf-8") in original)
            or (plan.operation == "shell_remove"
                and plan.managed_block.encode("utf-8") not in original)
        )
    ):
        return ShellResult(
            "already_integrated" if plan.operation == "shell_install"
            else "already_removed",
            plan.plan_id, plan.profile_path, _backup_path(plan),
        )
    if (exists != plan.original_exists or _digest(original) != plan.original_sha256
            or (exists and mode != plan.profile_mode)):
        raise ShellIntegrationError("profile_changed")
    result = _result_bytes(plan, original)
    if len(result) > MAX_PROFILE_BYTES:
        raise ShellIntegrationError("file_too_large")
    if _digest(result) != plan.result_sha256:
        raise ShellIntegrationError("plan_integrity_failed")
    backup = Path(_backup_path(plan))
    if backup.parent.exists():
        if backup.parent.is_symlink() or not backup.parent.is_dir():
            raise ShellIntegrationError("backup_directory_invalid")
    else:
        backup.parent.mkdir(mode=0o700)
    _write_exclusive(backup, original, 0o600)
    replaced = False
    try:
        if plan.result_exists:
            _replace_file(profile, result, plan.profile_mode)
        else:
            profile.unlink()
        replaced = True
        _verify_result(plan)
    except Exception as error:
        if replaced and not _restore_profile(plan, result, original):
            raise ShellIntegrationError("recovery_required") from error
        if isinstance(error, ShellIntegrationError):
            raise
        raise ShellIntegrationError("apply_failed") from error
    return ShellResult(
        "integrated" if plan.operation == "shell_install" else "removed",
        plan.plan_id, plan.profile_path, str(backup),
    )


def verify_shell_plan(plan: ShellPlan) -> ShellResult:
    _validate_plan(plan)
    try:
        _verify_result(plan)
    except ShellIntegrationError as error:
        raise ShellIntegrationError("verification_failed") from error
    return ShellResult("verified", plan.plan_id, plan.profile_path, _backup_path(plan))


def serialize_shell_plan(plan: ShellPlan) -> str:
    return _canonical_json(asdict(plan)) + "\n"


def _make_plan(
    operation: str,
    shell: str,
    home: Path,
    profile: Path,
    script: Path,
    syntax: Path | None,
    original_exists: bool,
    profile_mode: int,
    original: bytes,
    block: str,
    result_exists: bool,
    result: bytes,
    preconditions: tuple[str, ...],
    postconditions: tuple[str, ...],
    backout: tuple[str, ...],
) -> ShellPlan:
    if len(result) > MAX_PROFILE_BYTES:
        raise ShellIntegrationError("file_too_large")
    source_files = (
        tuple(_source_state(path) for path in _source_paths(script, syntax, shell))
        if operation == "shell_install" else ()
    )
    unsigned = {
        "schema_version": SHELL_PLAN_SCHEMA_VERSION,
        "operation": operation,
        "shell": shell,
        "home_root": str(home),
        "profile_path": str(profile),
        "shell_script_path": str(script),
        "syntax_highlighting_path": None if syntax is None else str(syntax),
        "original_exists": original_exists,
        "profile_mode": profile_mode,
        "original_sha256": _digest(original),
        "managed_block": block,
        "managed_block_sha256": _digest(block.encode("utf-8")),
        "result_exists": result_exists,
        "result_sha256": _digest(result),
        "preconditions": list(preconditions),
        "postconditions": list(postconditions),
        "backout": list(backout),
        "source_files": [asdict(source) for source in source_files],
    }
    return ShellPlan(
        SHELL_PLAN_SCHEMA_VERSION, operation, shell, str(home), str(profile),
        str(script), None if syntax is None else str(syntax), original_exists,
        profile_mode, unsigned["original_sha256"], block,
        unsigned["managed_block_sha256"],
        result_exists, unsigned["result_sha256"],
        preconditions, postconditions, backout,
        _digest(_canonical_json(unsigned).encode()), source_files,
    )


def _validate_plan(plan: ShellPlan) -> None:
    if (
        type(plan.schema_version) is not int
        or plan.schema_version != SHELL_PLAN_SCHEMA_VERSION
        or plan.operation not in ("shell_install", "shell_remove")
        or plan.shell not in ("bash", "zsh")
        or type(plan.original_exists) is not bool
        or type(plan.result_exists) is not bool
        or type(plan.profile_mode) is not int
        or plan.profile_mode < 0
        or plan.profile_mode > 0o777
    ):
        raise ShellIntegrationError("unsupported_plan")
    if any(type(value) is not str for value in (
        plan.operation, plan.shell, plan.home_root, plan.profile_path,
        plan.shell_script_path, plan.managed_block,
    )) or (plan.syntax_highlighting_path is not None
           and type(plan.syntax_highlighting_path) is not str):
        raise ShellIntegrationError("invalid_plan")
    for conditions in (plan.preconditions, plan.postconditions, plan.backout):
        if type(conditions) is not tuple or any(type(item) is not str for item in conditions):
            raise ShellIntegrationError("invalid_plan")
    home = _existing_directory(plan.home_root, "invalid_plan")
    if Path(plan.profile_path) != _profile_path(home, plan.shell):
        raise ShellIntegrationError("invalid_plan")
    script, syntax = _parse_managed_block(plan.managed_block, plan.shell)
    if str(script) != plan.shell_script_path:
        raise ShellIntegrationError("invalid_plan")
    if (None if syntax is None else str(syntax)) != plan.syntax_highlighting_path:
        raise ShellIntegrationError("invalid_plan")
    expected_paths = (
        tuple(str(path) for path in _source_paths(script, syntax, plan.shell))
        if plan.operation == "shell_install" else ()
    )
    if (type(plan.source_files) is not tuple
            or any(type(source) is not ShellSource for source in plan.source_files)
            or tuple(source.path for source in plan.source_files) != expected_paths):
        raise ShellIntegrationError("invalid_plan")
    for source in plan.source_files:
        if (type(source.sha256) is not str or not _DIGEST.fullmatch(source.sha256)
                or type(source.mode) is not int or not 0 <= source.mode <= 0o777):
            raise ShellIntegrationError("invalid_plan")
    if plan.operation == "shell_install" and (
        not plan.result_exists
        or _block_original_exists(plan.managed_block) != plan.original_exists
        or (not plan.original_exists and plan.profile_mode != 0o600)
    ):
        raise ShellIntegrationError("invalid_plan")
    if plan.operation == "shell_remove" and not plan.original_exists:
        raise ShellIntegrationError("invalid_plan")
    if any(
        type(value) is not str or not _DIGEST.fullmatch(value)
        for value in (
            plan.original_sha256, plan.managed_block_sha256,
            plan.result_sha256, plan.plan_id,
        )
    ):
        raise ShellIntegrationError("invalid_plan")
    if _digest(plan.managed_block.encode("utf-8")) != plan.managed_block_sha256:
        raise ShellIntegrationError("plan_integrity_failed")
    unsigned = asdict(plan)
    claimed = unsigned.pop("plan_id")
    if claimed != _digest(_canonical_json(unsigned).encode()):
        raise ShellIntegrationError("plan_integrity_failed")


def _verify_result(plan: ShellPlan) -> None:
    _verify_sources(plan)
    exists, content, mode = _profile_state(Path(plan.profile_path))
    if (exists != plan.result_exists or _digest(content) != plan.result_sha256
            or (exists and mode != plan.profile_mode)):
        raise ShellIntegrationError("profile_changed")
    occurrences = content.count(plan.managed_block.encode("utf-8"))
    if (
        (plan.operation == "shell_install" and occurrences != 1)
        or (plan.operation == "shell_remove" and occurrences != 0)
    ):
        raise ShellIntegrationError("managed_block_mismatch")


def _source_paths(script: Path, syntax: Path | None, shell: str) -> tuple[Path, ...]:
    # A fixed Core dependency contract, never recursive shell-code discovery.
    paths = [script]
    if script.name == "byte-shell.sh":
        paths.append(script.with_name(
            "byte-shell-bash.sh" if shell == "bash" else "byte-shell-zsh.zsh"
        ))
    if syntax is not None and syntax not in paths:
        paths.append(syntax)
    return tuple(paths)


def _source_state(path: Path) -> ShellSource:
    regular = _regular_file(path, "invalid_source_file")
    # Preserve the selected path: resolving a replacement parent symlink must
    # not silently redirect a previously reviewed source.
    if regular != path:
        raise ShellIntegrationError("invalid_source_file")
    before = regular.stat()
    data = _read_bounded(regular, MAX_SOURCE_BYTES)
    after = regular.stat()
    if (before.st_dev, before.st_ino, before.st_mode, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_mode, after.st_mtime_ns
    ):
        raise ShellIntegrationError("file_changed_during_read")
    mode = stat.S_IMODE(after.st_mode)
    if mode > 0o777:
        raise ShellIntegrationError("invalid_source_file")
    return ShellSource(str(path), _digest(data), mode)


def _verify_sources(plan: ShellPlan) -> None:
    for source in plan.source_files:
        try:
            current = _source_state(Path(source.path))
        except (ShellIntegrationError, OSError) as error:
            raise ShellIntegrationError("source_changed") from error
        if current != source:
            raise ShellIntegrationError("source_changed")


def _source_tuple(value: Any) -> tuple[ShellSource, ...]:
    if type(value) is not list or any(
        type(item) is not dict or set(item) != {"path", "sha256", "mode"}
        or type(item["path"]) is not str for item in value
    ):
        raise ShellIntegrationError("invalid_plan")
    return tuple(ShellSource(**item) for item in value)


def _result_bytes(plan: ShellPlan, original: bytes) -> bytes:
    if plan.operation == "shell_install":
        _require_no_markers(original)
        separator = int(
            plan.managed_block.splitlines()[1].rsplit(" ", 1)[1]
        )
        return original + b"\n" * separator + plan.managed_block.encode("utf-8")
    block = _extract_block(original)
    if block != plan.managed_block:
        raise ShellIntegrationError("managed_block_mismatch")
    return _remove_block(original, block)


def _managed_block(
    script: Path,
    syntax: Path | None,
    separator_newlines: int,
    original_exists: bool,
) -> str:
    lines = [
        START_MARKER,
        f"# Byte Core separator newlines: {separator_newlines}",
        f"# Byte Core profile originally existed: {'yes' if original_exists else 'no'}",
        f". {_shell_quote(str(script))}",
    ]
    if syntax is not None:
        lines.append(f". {_shell_quote(str(syntax))}")
    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def _parse_managed_block(
    block: str, shell: str
) -> tuple[Path, Path | None]:
    lines = block.splitlines()
    if (
        len(lines) not in (5, 6)
        or lines[0] != START_MARKER
        or lines[-1] != END_MARKER
        or not lines[1].startswith("# Byte Core separator newlines: ")
        or lines[2] not in (
            "# Byte Core profile originally existed: yes",
            "# Byte Core profile originally existed: no",
        )
    ):
        raise ShellIntegrationError("malformed_managed_block")
    try:
        separator = int(lines[1].rsplit(" ", 1)[1])
    except (ValueError, IndexError) as error:
        raise ShellIntegrationError("malformed_managed_block") from error
    if separator not in (0, 1, 2):
        raise ShellIntegrationError("malformed_managed_block")
    paths = [_parse_source_line(line) for line in lines[3:-1]]
    if shell == "bash" and len(paths) != 1:
        raise ShellIntegrationError("malformed_managed_block")
    return paths[0], paths[1] if len(paths) == 2 else None


def _parse_source_line(line: str) -> Path:
    if not line.startswith(". '") or not line.endswith("'"):
        raise ShellIntegrationError("malformed_managed_block")
    encoded = line[3:-1]
    value = encoded.replace("'\"'\"'", "'")
    path = Path(value)
    if (not path.is_absolute() or "\n" in value or "\r" in value
            or "\0" in value or line != ". " + _shell_quote(value)):
        raise ShellIntegrationError("malformed_managed_block")
    return path


def _extract_block(content: bytes) -> str:
    # Profile bytes belong to the operator and need not use Core's encoding.
    # Only the managed block is UTF-8; inspect markers without decoding anything
    # outside it so removal can preserve legacy comments and other unrelated data.
    start_marker = START_MARKER.encode("utf-8")
    end_marker = END_MARKER.encode("utf-8")
    if content.count(start_marker) != 1 or content.count(end_marker) != 1:
        raise ShellIntegrationError(
            "managed_block_absent"
            if start_marker not in content and end_marker not in content
            else "malformed_managed_block"
        )
    start = content.index(start_marker)
    if content.index(end_marker) < start or (start and content[start - 1:start] != b"\n"):
        raise ShellIntegrationError("malformed_managed_block")
    end = content.index(end_marker, start) + len(end_marker)
    if end < len(content) and content[end:end + 1] != b"\n":
        raise ShellIntegrationError("malformed_managed_block")
    if end < len(content):
        end += 1
    try:
        return content[start:end].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ShellIntegrationError("malformed_managed_block") from error


def _remove_block(content: bytes, block: str) -> bytes:
    encoded = block.encode("utf-8")
    if content.count(encoded) != 1:
        raise ShellIntegrationError("managed_block_mismatch")
    lines = block.splitlines()
    separator = int(lines[1].rsplit(" ", 1)[1])
    start = content.index(encoded)
    prefix_start = start - separator
    if prefix_start < 0 or content[prefix_start:start] != b"\n" * separator:
        raise ShellIntegrationError("managed_block_mismatch")
    return content[:prefix_start] + content[start + len(encoded):]


def _block_original_exists(block: str) -> bool:
    lines = block.splitlines()
    if len(lines) < 3:
        raise ShellIntegrationError("malformed_managed_block")
    if lines[2] == "# Byte Core profile originally existed: yes":
        return True
    if lines[2] == "# Byte Core profile originally existed: no":
        return False
    raise ShellIntegrationError("malformed_managed_block")


def _profile_separator(content: bytes) -> bytes:
    separator = b"" if not content or content.endswith(b"\n") else b"\n"
    if content and not content.endswith(b"\n\n"):
        separator += b"\n"
    return separator


def _require_no_markers(content: bytes) -> None:
    if START_MARKER.encode() in content or END_MARKER.encode() in content:
        raise ShellIntegrationError("managed_block_conflict")


def _profile_path(home: Path, shell: str) -> Path:
    if shell == "bash":
        return home / ".bashrc"
    if shell == "zsh":
        return home / ".zshrc"
    raise ShellIntegrationError("unsupported_shell")


def _profile_state(path: Path) -> tuple[bool, bytes, int]:
    if path.is_symlink():
        raise ShellIntegrationError("invalid_profile")
    if not path.exists():
        return False, b"", 0o600
    regular = _regular_file(path, "invalid_profile")
    return (
        True,
        _read_bounded(regular, MAX_PROFILE_BYTES),
        stat.S_IMODE(regular.stat().st_mode),
    )


def _backup_path(plan: ShellPlan) -> str:
    name = Path(plan.profile_path).name
    return str(
        Path(plan.home_root) / ".byte-backups"
        / f"{name}.{plan.plan_id}.{plan.operation}.bak"
    )


def _restore_profile(
    plan: ShellPlan, expected: bytes, original: bytes
) -> bool:
    profile = Path(plan.profile_path)
    try:
        exists, current, mode = _profile_state(profile)
        if (exists != plan.result_exists or current != expected
                or (exists and mode != plan.profile_mode)):
            return False
        if plan.original_exists:
            _replace_file(profile, original, plan.profile_mode)
        else:
            profile.unlink()
    except (OSError, ShellIntegrationError):
        return False
    return True


def _shell_quote(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ShellIntegrationError("invalid_path")
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _existing_directory(value: str | os.PathLike[str], code: str) -> Path:
    try:
        path = Path(value)
        if not path.is_absolute() or path.is_symlink():
            raise ShellIntegrationError(code)
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ShellIntegrationError(code) from error
    if not resolved.is_dir():
        raise ShellIntegrationError(code)
    return resolved


def _regular_file(value: str | os.PathLike[str], code: str) -> Path:
    try:
        path = Path(value)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ShellIntegrationError(code)
        resolved = path.resolve(strict=True)
    except ShellIntegrationError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ShellIntegrationError(code) from error
    return resolved


def _read_bounded(path: Path, maximum: int) -> bytes:
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ShellIntegrationError("file_too_large")
        data = path.read_bytes()
        after = path.stat()
    except OSError as error:
        raise ShellIntegrationError("file_read_error") from error
    if (
        len(data) > maximum
        or (before.st_dev, before.st_ino, before.st_size, before.st_mode, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mode, after.st_mtime_ns)
    ):
        raise ShellIntegrationError("file_changed_during_read")
    return data


def _write_exclusive(path: Path, data: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags, mode)
    except OSError as error:
        raise ShellIntegrationError("backup_exists") from error
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def _replace_file(path: Path, data: bytes, mode: int) -> None:
    temporary = path.with_name(f".{path.name}.byte-tmp")
    _write_exclusive(temporary, data, mode)
    try:
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _string_tuple(value: Any) -> tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ShellIntegrationError("invalid_plan")
    return tuple(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
