"""Offline helper onboarding with exact approval and exclusive TOML publication."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import stat
import tomllib
import uuid

from . import helpers_config
from .inventory_io import (
    MAX_BYTES, _open_parent, check_seal, digest, path, read_bytes,
    require_absent, seal,
)


class SetupError(ValueError):
    """Stable, value-free setup error."""


def _source(settings: str) -> tuple[bytes, dict]:
    data = read_bytes(settings)
    try:
        document = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError):
        raise helpers_config.HelperConfigError("cannot parse helpers config: use valid UTF-8 TOML") from None
    # Validate the exact bytes bound to the plan, never a separate file read.
    return data, helpers_config.validate(document)


def _readiness(config: dict) -> dict:
    checks = []

    def report(setting, status, detail):
        checks.append({"setting": setting, "status": status, "detail": detail})

    shell = config["shell"]
    development = shell.get("development_directory")
    if development:
        report("shell.development_directory", "ready" if Path(development).is_dir() else "missing",
               "Configured development directory must exist.")
    else:
        report("shell.development_directory", "unconfigured", "Set this path before using dev.")
    highlighter = shell.get("highlighting_file")
    if highlighter:
        readable = Path(highlighter).is_file() and os.access(highlighter, os.R_OK)
        report("shell.highlighting_file", "ready" if readable else "missing",
               "Selected code must be readable; its content and compatibility are not checked.")
    if shell["highlighting"]:
        report("shell.highlighting", "manual", "Requires Zsh and review of the selected code before sourcing.")
    assistant = config["assistant"]
    executable = assistant.get("executable")
    if executable:
        available = (Path(executable).is_file() and os.access(executable, os.X_OK)
                     if "/" in executable else shutil.which(executable) is not None)
        report("assistant.executable", "ready" if available else "missing",
               "Only executable availability was checked; application behavior is untested.")
    elif assistant:
        report("assistant.executable", "missing", "Set an executable to use configured launch arguments.")
    else:
        report("assistant", "unconfigured", "Select an executable and literal new/resume arguments to use byten/byter.")
    if executable:
        for key, command in (("new_args", "byten"), ("resume_args", "byter")):
            report(f"assistant.{key}", "ready" if key in assistant else "unconfigured",
                   f"Set this argument array before using {command}; an explicit empty array is allowed.")
    for index, repo in enumerate(config["repositories"]):
        report(f"repositories[{index}].path", "ready" if Path(repo["path"]).is_dir() else "missing",
               "Only directory existence was checked; review a separate sync plan before repository operations.")
    if config["devices"]:
        report("devices", "manual", "Device readiness is unknown; separately review reachability or wake plans.")
    return {"ready": all(item["status"] != "missing" for item in checks), "checks": checks,
            "boundary": "Offline existence checks only; no applications, shell code, Git commands, or network operations were run."}


def check(settings: str) -> dict:
    """Read only the selected settings and check explicit local prerequisites."""
    data, config = _source(settings)
    return {"schema_version": 1, "settings_sha256": digest(data), **_readiness(config)}


def _directory_identity(target: Path) -> dict:
    directory = _open_parent(target)
    try:
        info = os.fstat(directory)
        return {"device": info.st_dev, "inode": info.st_ino}
    finally:
        os.close(directory)


def _next_steps(output: str, home_root=None, shell=None, shell_script=None) -> list[dict]:
    steps = [{"action": "select_settings", "command": "export BYTE_CORE_HELPERS_CONFIG=" + shlex.quote(output),
              "detail": "Run in the chosen shell before sourcing Byte. A persistent selector is a separate deployment-owned edit."},
             {"action": "validate", "argv": ["byte", "helpers", "--config", output, "config", "validate"]}]
    if home_root is not None:
        steps.append({"action": "shell_plan", "argv": ["byte", "shell", "plan", "--home-root", home_root,
                      "--shell", shell, "--shell-script", shell_script],
                      "detail": "Save privately, review, then separately approve and verify this shell lifecycle plan."})
    else:
        steps.append({"action": "shell_setup", "detail": "Select an explicit home root, Bash or Zsh, and shell asset; use byte shell plan for separate profile approval."})
    steps.append({"action": "session_check", "detail": "After loading the reviewed shell asset, run bytehelp and bytewhere. Test selected optional features individually."})
    return steps


def build_plan(settings: str, output: str, *, home_root=None, shell=None, shell_script=None) -> dict:
    """Bind an existing settings file and an absent destination; never write."""
    source = path(settings)
    target = require_absent(output)
    data, config = _source(str(source))
    readiness = _readiness(config)
    if not readiness["ready"]:
        raise SetupError("setup_prerequisites_missing: run byte setup check --settings with the selected file")
    options = (home_root, shell, shell_script)
    if any(value is not None for value in options):
        if any(value is None for value in options) or shell not in {"bash", "zsh"}:
            raise SetupError("setup_shell_options_incomplete")
        home_root = str(path(home_root))
        if not Path(home_root).is_dir():
            raise SetupError("setup_home_root_unavailable")
        shell_script = str(path(shell_script))
        # Validate the explicit asset as bounded regular input, without executing it.
        read_bytes(shell_script)
        if shell == "bash" and config["shell"]["highlighting"]:
            raise SetupError("setup_highlighting_requires_zsh")
    return seal("helper_setup_plan", settings=str(source), settings_sha256=digest(data),
                output=str(target), output_parent=_directory_identity(target), mode="0600",
                shell_selection={"home_root": home_root, "shell": shell, "shell_script": shell_script},
                prerequisites=readiness, next_steps=_next_steps(str(target), home_root, shell, shell_script),
                backout={"action": "manual_remove_new_file", "path": str(target), "sha256": digest(data),
                         "detail": "Remove only this newly created file after checking its path and unchanged digest. Preserve edited files. Setup does not modify profiles."})


def _plan(value: object) -> dict:
    plan = check_seal(value, "helper_setup_plan")
    expected = {"schema_version", "kind", "id", "settings", "settings_sha256", "output", "output_parent",
                "mode", "shell_selection", "prerequisites", "next_steps", "backout"}
    if (set(plan) != expected or plan["mode"] != "0600"
            or type(plan["settings"]) is not str or type(plan["output"]) is not str
            or type(plan["settings_sha256"]) is not str
            or len(plan["settings_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in plan["settings_sha256"])
            or type(plan["shell_selection"]) is not dict
            or set(plan["shell_selection"]) != {"home_root", "shell", "shell_script"}
            or any(value is not None and type(value) is not str
                   for value in plan["shell_selection"].values())
            or type(plan["output_parent"]) is not dict
            or set(plan["output_parent"]) != {"device", "inode"}
            or any(type(value) is not int for value in plan["output_parent"].values())):
        raise SetupError("setup_invalid_plan")
    return plan


def _publish(target: Path, data: bytes, expected_parent: dict) -> None:
    """Link a complete private temporary file into an absent destination."""
    directory = None
    temporary = ".byte-setup-" + uuid.uuid4().hex
    created = False
    try:
        require_absent(target)
        directory = _open_parent(target)
        info = os.fstat(directory)
        if {"device": info.st_dev, "inode": info.st_ino} != expected_parent:
            raise SetupError("setup_plan_stale")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        created = True
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # An ancestor changed since opening the directory must not redirect publication.
        if _directory_identity(target) != expected_parent:
            raise SetupError("setup_plan_stale")
        os.link(temporary, target.name, src_dir_fd=directory, dst_dir_fd=directory,
                follow_symlinks=False)
    except FileExistsError:
        raise SetupError("setup_target_exists") from None
    except OSError:
        raise SetupError("setup_write_failed") from None
    finally:
        if directory is not None:
            try:
                if created:
                    os.unlink(temporary, dir_fd=directory)
            except OSError:
                raise SetupError("setup_recovery_required") from None
            finally:
                os.close(directory)


def verify(value: object) -> dict:
    """Check the published file against its reviewed bytes, directory, and mode."""
    plan = _plan(value)
    target = path(plan["output"], output=True)
    directory = None
    try:
        directory = _open_parent(target)
        parent_info = os.fstat(directory)
        if {"device": parent_info.st_dev, "inode": parent_info.st_ino} != plan["output_parent"]:
            raise SetupError("setup_verification_failed")
        fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_size > MAX_BYTES):
                raise SetupError("setup_verification_failed")
            data = stream.read(MAX_BYTES + 1)
    except OSError:
        raise SetupError("setup_verification_failed") from None
    finally:
        if directory is not None:
            os.close(directory)
    if len(data) > MAX_BYTES or digest(data) != plan["settings_sha256"]:
        raise SetupError("setup_verification_failed")
    return {"code": "verified", "plan_id": plan["id"], "next_steps": plan["next_steps"]}


def apply(value: object, approval: str) -> dict:
    plan = _plan(value)
    if approval != plan["id"]:
        raise SetupError("setup_not_approved")
    fresh = build_plan(plan["settings"], plan["output"], **plan["shell_selection"])
    if fresh != plan:
        raise SetupError("setup_plan_stale")
    data = read_bytes(plan["settings"])
    if digest(data) != plan["settings_sha256"]:
        raise SetupError("setup_plan_stale")
    _publish(path(plan["output"], output=True), data, plan["output_parent"])
    result = verify(plan)
    return {**result, "code": "settings_saved"}
