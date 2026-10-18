"""Small local shell backends; configuration is argv data, never shell code."""

from __future__ import annotations

import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time
import unicodedata


class ShellHelperError(ValueError):
    """Actionable failure before launching an application."""


def _git_project() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=False,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise ShellHelperError("Git is required; install it or select an available PATH") from error
    if result.returncode:
        raise ShellHelperError("run this helper inside a Git worktree")
    return os.fsdecode(result.stdout.removesuffix(b"\n"))


def run_assistant(config: dict, mode: str, args: list[str]) -> int:
    """Launch the selected adapter once, at the current worktree's top level.

    The operator supplies application-specific new/resume arguments. A literal
    {project} token is replaced without interpreting any other punctuation.
    """
    if mode not in {"new", "resume"}:
        raise ShellHelperError("assistant mode must be new or resume")
    settings = config.get("assistant", {})
    executable = settings.get("executable")
    arguments = settings.get(f"{mode}_args")
    if not executable or arguments is None:
        raise ShellHelperError(f"configure assistant.executable and assistant.{mode}_args first")
    if not isinstance(executable, str) or not isinstance(arguments, list) or any(
        not isinstance(argument, str) or "\x00" in argument for argument in [*arguments, *args]
    ):
        raise ShellHelperError("assistant executable and arguments must be validated strings")
    if executable.startswith("-") or ("/" in executable and (
            not Path(executable).is_absolute() or ".." in Path(executable).parts)):
        raise ShellHelperError("assistant.executable must be a command name or absolute path without parent traversal")
    resolved = shutil.which(executable)
    if resolved is None:
        raise ShellHelperError("configured assistant executable is unavailable; install or configure it explicitly")
    project = _git_project()
    argv = [resolved, *(argument.replace("{project}", project) for argument in arguments), *args]
    try:
        return subprocess.run(argv, cwd=project, check=False).returncode
    except OSError as error:
        raise ShellHelperError("configured assistant could not be launched") from error


def git_status(args: list[str]) -> int:
    """Run only Git status; additional arguments follow the fixed subcommand."""
    _git_project()
    try:
        return subprocess.run(["git", "status", *args], check=False).returncode
    except OSError as error:
        raise ShellHelperError("Git status could not be launched") from error


def _prompt_git(arguments: list[str], deadline: float) -> str | None:
    """Capture at most 2 MiB within the shared prompt deadline."""
    command = ["git", "--no-pager", "--no-optional-locks",
               "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
               "-c", "diff.external=", "-c", "submodule.recurse=false", *arguments]
    process = None
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                if not selector.select(remaining):
                    return None
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > 2 * 1024 * 1024:
                    return None
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if process.returncode not in (0, 1) or (process.returncode == 1 and arguments[0] != "config"):
            return None
        return output.decode("utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()


def _prompt_git_segment() -> str:
    deadline = time.monotonic() + 2
    # Even Git status may execute a clean/process filter to refresh metadata.
    # A passive prompt omits Git context whenever any filter is configured.
    filters = _prompt_git(["config", "--name-only", "--get-regexp",
                           r"^(filter\..*\.(clean|smudge|process)|remote\..*\.(promisor|partialclonefilter)|extensions\.partialclone)$"], deadline)
    if filters is None or filters:
        return ""
    status = _prompt_git(["status", "--porcelain=v1", "--branch",
                          "--untracked-files=normal", "--ignore-submodules=all"], deadline)
    if not status or not status.startswith("## "):
        return ""
    lines = status.splitlines()
    branch = lines[0][3:].split("...")[0]
    if branch == "HEAD (no branch)":
        revision = _prompt_git(["rev-parse", "--short", "HEAD"], deadline)
        if not revision:
            return ""
        branch = "detached:" + revision.strip()
    for prefix in ("No commits yet on ", "Initial commit on "):
        if branch.startswith(prefix):
            branch = branch[len(prefix):]
    return " [" + branch + ("*" if len(lines) > 1 else "") + "]"


def prompt_text(config: dict, shell: str = "bash") -> str:
    """Render plain prompt data; never evaluate labels, paths, or Git text."""
    if shell not in {"bash", "zsh"}:
        raise ShellHelperError("prompt shell must be bash or zsh")
    settings = config.get("shell", {})
    text = settings.get("prompt_label", "Byte")
    if settings.get("prompt_directory", True):
        try:
            text += " " + (Path.cwd().name or "/")
        except OSError:
            text += " ?"
    if settings.get("prompt_git", True):
        text += _prompt_git_segment()
    text = "".join(character if not unicodedata.category(character).startswith("C") else "?"
                   for character in text)
    # Zsh performs percent expansion on the result of prompt substitution.
    return text.replace("%", "%%") if shell == "zsh" else text
