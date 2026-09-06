"""Bounded private-local input and exclusive inventory publication."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
CORE_ROOT = Path(__file__).resolve().parents[2]


class InventoryError(Exception):
    """Only stable codes may cross the CLI error boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       allow_nan=False, indent=2) + "\n").encode("utf-8")


def seal(kind: str, **fields: object) -> dict:
    unsigned = {"schema_version": 1, "kind": kind, **fields}
    return {**unsigned, "id": digest(encode(unsigned))}


def check_seal(value: object, kind: str) -> dict:
    if not isinstance(value, dict):
        raise InventoryError("invalid_inventory_input")
    unsigned = {k: v for k, v in value.items() if k != "id"}
    if (type(value.get("schema_version")) is not int
            or value["schema_version"] != 1 or value.get("kind") != kind
            or value.get("id") != digest(encode(unsigned))):
        raise InventoryError("invalid_inventory_input")
    return value


def text(value: object, *, limit: int = 160, empty: bool = False) -> str:
    if (not isinstance(value, str) or len(value) > limit
            or (not empty and not value.strip())
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise InventoryError("invalid_inventory_input")
    return value


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError("invalid_inventory_input")
        result[key] = value
    return result


def decode(data: bytes) -> object:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: _bad_json())
    except (UnicodeError, ValueError, RecursionError):
        raise InventoryError("invalid_inventory_input") from None


def _bad_json() -> None:
    raise InventoryError("invalid_inventory_input")


def path(value: str | os.PathLike[str], *, output: bool = False) -> Path:
    try:
        candidate = Path(value)
        if not candidate.is_absolute() or ".." in candidate.parts:
            raise InventoryError("inventory_path_invalid")
        for part in (candidate, *candidate.parents):
            if part.is_symlink():
                raise InventoryError("inventory_path_invalid")
        if candidate.parent.resolve(strict=True) != candidate.parent:
            raise InventoryError("inventory_path_invalid")
        if output:
            if candidate == CORE_ROOT or CORE_ROOT in candidate.parents:
                raise InventoryError("inventory_output_in_repository")
            if ".git" in candidate.parts:
                raise InventoryError("inventory_output_in_repository")
        return candidate
    except (OSError, ValueError, TypeError, RuntimeError):
        raise InventoryError("inventory_path_invalid") from None


def read_bytes(value: str | os.PathLike[str]) -> bytes:
    source = path(value)
    try:
        parent = _open_parent(source)
        try:
            fd = os.open(source.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent)
        finally:
            os.close(parent)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise InventoryError("inventory_input_limit")
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise InventoryError("inventory_input_limit")
        return data
    except OSError:
        raise InventoryError("inventory_read_failed") from None


def read_json(value: str | os.PathLike[str]) -> object:
    return decode(read_bytes(value))


def require_absent(value: str | os.PathLike[str]) -> Path:
    target = path(value, output=True)
    if target.exists():
        raise InventoryError("inventory_target_exists")
    return target


def _open_parent(target: Path) -> int:
    """Walk from the root with directory FDs so ancestors cannot redirect via links."""
    current = os.open(target.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in target.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=current)
            os.close(current)
            current = child
        return current
    except OSError:
        os.close(current)
        raise


def publish(value: str | os.PathLike[str], content: object) -> None:
    """Publish a complete 0600 file without replacing an existing target."""
    target = require_absent(value)
    data = encode(content)
    if len(data) > MAX_BYTES:
        raise InventoryError("inventory_input_limit")
    directory = None
    temporary = ".byte-inventory-" + uuid.uuid4().hex
    created = False
    linked = False
    try:
        directory = _open_parent(target)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        created = True
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target.name, src_dir_fd=directory,
                dst_dir_fd=directory, follow_symlinks=False)
        linked = True
    except FileExistsError:
        raise InventoryError("inventory_target_exists") from None
    except OSError:
        raise InventoryError("inventory_write_failed") from None
    finally:
        if directory is not None:
            try:
                if created:
                    os.unlink(temporary, dir_fd=directory)
            except OSError:
                raise InventoryError("inventory_recovery_required") from None
            finally:
                os.close(directory)
    if linked and read_bytes(target) != data:
        raise InventoryError("inventory_verification_failed")
