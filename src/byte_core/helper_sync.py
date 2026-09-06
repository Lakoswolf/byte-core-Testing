"""Explicit, bounded Git synchronization; plans are private local artifacts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time

TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 2 * 1024 * 1024


class SyncError(ValueError):
    """A safe error code, never raw Git or repository output."""


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def _git(path, *args, allowed=(0,)):
    # Ambient Git overrides must not redirect the explicitly approved repository.
    config_selectors = {"GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_GLOBAL"}
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_") or key in config_selectors}
    environment.update(GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    process = None
    try:
        process = subprocess.Popen(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
             "-c", "submodule.recurse=false", "-c", "maintenance.auto=false",
             "-c", "gc.auto=0", "-c", "protocol.ext.allow=never", "-C", str(path), *args],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment,
            stdin=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + TIMEOUT_SECONDS
        output = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SyncError("sync_git_timeout")
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, min(65536, MAX_OUTPUT_BYTES + 1 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(chunk)
                        if len(output) > MAX_OUTPUT_BYTES:
                            raise SyncError("sync_git_output_limit")
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as error:
            raise SyncError("sync_git_timeout") from error
    except OSError as error:
        raise SyncError("sync_git_unavailable") from error
    finally:
        if process is not None:
            # Descendant transports may retain the pipe after Git exits. Terminate
            # the entire session on timeout/output failure, not only the Git PID.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdout.close()
    if process.returncode not in allowed:
        raise SyncError("sync_git_failed")
    try:
        return process.returncode, output.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise SyncError("sync_git_output_invalid") from error


def _out(path, *args):
    return _git(path, *args)[1].rstrip("\n")


def _directory_identity(value):
    path = Path(value)
    if (not path.is_absolute() or ".." in path.parts or
            any(part.is_symlink() for part in (path, *path.parents))):
        raise SyncError("sync_repository_path_invalid")
    try:
        info = path.stat(follow_symlinks=False)
    except OSError as error:
        raise SyncError("sync_repository_path_invalid") from error
    if not stat.S_ISDIR(info.st_mode):
        raise SyncError("sync_repository_path_invalid")
    return {"device": info.st_dev, "inode": info.st_ino}


def _repositories(config):
    repositories = config.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise SyncError("sync_repositories_required")
    result, paths, names = [], set(), set()
    for item in repositories:
        if not isinstance(item, dict) or set(item) != {"name", "path", "remote", "branch"}:
            raise SyncError("sync_repository_invalid")
        if any(not isinstance(value, str) or not value or
               any(ord(char) < 32 or ord(char) == 127 for char in value)
               for value in item.values()):
            raise SyncError("sync_repository_invalid")
        path = Path(item["path"])
        _directory_identity(path)
        path = str(path.resolve())
        if path in paths or item["name"] in names:
            raise SyncError("sync_repository_duplicate")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", item["remote"]):
            raise SyncError("sync_remote_invalid")
        if item["branch"].startswith("-") or _git(path, "check-ref-format", "--branch",
                                                    item["branch"], allowed=(0, 128))[0]:
            raise SyncError("sync_branch_invalid")
        # check-ref-format --branch can expand @{-1}; reject such shorthand.
        if _git(path, "check-ref-format", "refs/heads/" + item["branch"],
                allowed=(0, 1))[0]:
            raise SyncError("sync_branch_invalid")
        paths.add(path)
        names.add(item["name"])
        result.append(dict(item, path=path))
    return result


def _snapshot(repository):
    path, branch, remote = (repository[key] for key in ("path", "branch", "remote"))
    worktree_identity = _directory_identity(path)
    if (Path(path) / ".git").is_symlink():
        raise SyncError("sync_repository_path_invalid")
    # Even `git status` can execute clean/process filters. Inspect configuration
    # before any index/worktree comparison; never bypass required filter behavior.
    configuration = _out(path, "config", "--null", "--list")
    keys = [entry.split("\n", 1)[0].lower() for entry in configuration.split("\0")]
    if any(re.fullmatch(r"filter\..+\.(clean|smudge|process)", key) for key in keys):
        raise SyncError("sync_filters_unsupported")
    if any(key == "extensions.partialclone" or re.fullmatch(r"remote\..+\.promisor", key)
           for key in keys):
        raise SyncError("sync_partial_clone_unsupported")
    if any(re.fullmatch(r"branch\..+\.mergeoptions", key) for key in keys):
        raise SyncError("sync_merge_options_unsupported")
    if _out(path, "rev-parse", "--is-bare-repository") != "false":
        raise SyncError("sync_bare_repository")
    if str(Path(_out(path, "rev-parse", "--show-toplevel")).resolve()) != path:
        raise SyncError("sync_repository_root_required")
    git_dir = Path(_out(path, "rev-parse", "--absolute-git-dir"))
    common_dir = _out(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    git_identity = _directory_identity(git_dir)
    common_identity = _directory_identity(common_dir)
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "REBASE_HEAD",
                   "rebase-merge", "rebase-apply", "sequencer", "BISECT_LOG", "index.lock"):
        if (git_dir / marker).exists():
            raise SyncError("sync_operation_in_progress")
    code, current_branch = _git(path, "symbolic-ref", "--quiet", "HEAD", allowed=(0, 1))
    if code:
        raise SyncError("sync_detached_head")
    if any(entry.startswith("160000 ") for entry in
           _out(path, "ls-files", "--stage", "-z").split("\0")):
        raise SyncError("sync_submodules_unsupported")
    if _out(path, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise SyncError("sync_worktree_dirty")
    target_ref = "refs/heads/" + branch
    target_sha = _out(path, "rev-parse", "--verify", target_ref + "^{commit}")
    worktrees = _out(path, "worktree", "list", "--porcelain", "-z")
    current_path = None
    for field in worktrees.split("\0"):
        if field.startswith("worktree "):
            current_path = str(Path(field[9:]).resolve())
        if field == "branch " + target_ref and current_path != path:
            raise SyncError("sync_branch_in_other_worktree")
    if remote not in _out(path, "remote").splitlines():
        raise SyncError("sync_remote_missing")
    remote_ref = "refs/remotes/" + remote + "/" + branch
    code, remote_sha = _git(path, "rev-parse", "--verify", remote_ref + "^{commit}",
                            allowed=(0, 128))
    # Bind all effective Git configuration without including URLs or credentials in output.
    return {"repository": repository, "git_dir": str(git_dir), "common_dir": common_dir,
            "worktree_identity": worktree_identity, "git_identity": git_identity,
            "common_identity": common_identity,
            "starting_branch": current_branch.strip(), "starting_sha": _out(path, "rev-parse", "HEAD"),
            "target_ref": target_ref, "target_sha": target_sha, "remote_ref": remote_ref,
            "remote_sha": remote_sha.strip() if not code else None,
            "worktrees_digest": _digest(worktrees), "git_config_digest": _digest(configuration),
            "worktree_status": "clean"}


def plan(config):
    """Read local state only. No remote contact or repository mutations."""
    repositories = _repositories(config)
    snapshots = [_snapshot(repository) for repository in repositories]
    if len({item["common_dir"] for item in snapshots}) != len(snapshots):
        raise SyncError("sync_shared_repository")
    body = {"version": 1, "kind": "canisync", "config_binding": _digest(config),
            "repositories": snapshots,
            "operations": ["fetch_selected_branch_and_prune_selected_tracking_ref",
                           "validate_all_fast_forwards", "switch_existing_branch", "fast_forward_only"],
            "remote_state": "unknown_until_approved_fetch",
            "recovery": "No automatic rollback. Starting branches and commit IDs are recorded."}
    return dict(body, id=_digest(body))


def _unchanged(before, after, *, fetched=False):
    ignored = {"remote_sha"} if fetched else set()
    if {k: v for k, v in before.items() if k not in ignored} != {
            k: v for k, v in after.items() if k not in ignored}:
        raise SyncError("sync_plan_stale")


def apply(config, proposed, approve):
    """Apply exactly the reviewed scope; report every attempted mutable phase."""
    if not isinstance(proposed, dict):
        raise SyncError("sync_plan_invalid")
    body = {key: value for key, value in proposed.items() if key != "id"}
    if proposed.get("id") != _digest(body) or approve != proposed.get("id"):
        raise SyncError("sync_plan_not_approved")
    current = plan(config)
    if current != proposed:
        raise SyncError("sync_plan_stale")
    snapshots = current["repositories"]
    report = {"status": "complete", "plan_id": proposed["id"], "repositories": [
        {"name": item["repository"]["name"], "path": item["repository"]["path"],
         "starting_branch": item["starting_branch"], "starting_sha": item["starting_sha"],
         "starting_target_sha": item["target_sha"], "fetch": "not_started",
         "switch": "not_started", "update": "not_started"} for item in snapshots]}
    try:
        for item, outcome in zip(snapshots, report["repositories"]):
            repository = item["repository"]
            _unchanged(item, _snapshot(repository))
            outcome["fetch"] = "attempted_may_have_changed_refs"
            _out(repository["path"], "fetch", "--prune", "--no-tags", "--no-recurse-submodules",
                 "--no-write-fetch-head", "--refmap=", repository["remote"],
                 "+refs/heads/" + repository["branch"] + ":" + item["remote_ref"])
            outcome["fetch"] = "complete"
        fetched = []
        for item in snapshots:
            after = _snapshot(item["repository"])
            _unchanged(item, after, fetched=True)
            if not after["remote_sha"] or _git(item["repository"]["path"], "merge-base",
                    "--is-ancestor", item["target_sha"], after["remote_sha"], allowed=(0, 1))[0]:
                raise SyncError("sync_fast_forward_unavailable")
            fetched.append(after)
        for item, after, outcome in zip(snapshots, fetched, report["repositories"]):
            repository = item["repository"]
            _unchanged(after, _snapshot(repository))
            if item["starting_branch"] != item["target_ref"]:
                outcome["switch"] = "attempted_may_have_changed_branch"
                _out(repository["path"], "switch", "--no-guess", "--no-overwrite-ignore",
                     "--", repository["branch"])
                outcome["switch"] = "complete"
            else:
                outcome["switch"] = "already_selected"
            selected = _snapshot(repository)
            if (selected["starting_branch"] != item["target_ref"] or
                    selected["starting_sha"] != item["target_sha"] or
                    selected["remote_sha"] != after["remote_sha"] or
                    any(selected[key] != item[key] for key in (
                        "git_config_digest", "worktree_identity", "git_identity",
                        "common_identity", "git_dir", "common_dir"))):
                raise SyncError("sync_plan_stale")
            outcome["update"] = "attempted_may_have_changed_head"
            _out(repository["path"], "merge", "--ff-only", "--no-edit", "--no-stat",
                 "--no-autostash", "--no-overwrite-ignore", after["remote_sha"])
            outcome["update"] = "complete"
            final = _snapshot(repository)
            if (final["starting_sha"] != after["remote_sha"] or
                    final["starting_branch"] != item["target_ref"] or
                    any(final[key] != selected[key] for key in (
                        "worktree_identity", "git_identity", "common_identity"))):
                raise SyncError("sync_verification_failed")
            outcome["final_branch"] = final["starting_branch"]
            outcome["final_sha"] = final["starting_sha"]
    except (SyncError, UnicodeError, OSError) as error:
        report["status"] = "partial" if any(item["fetch"] != "not_started" for item in
                                              report["repositories"]) else "failed"
        report["error"] = str(error) if isinstance(error, SyncError) else "sync_inspection_failed"
        report["recovery"] = "Inspect each repository before retrying. No automatic rollback was attempted."
        for item, outcome in zip(snapshots, report["repositories"]):
            try:
                outcome["observed_branch"] = _out(item["repository"]["path"], "symbolic-ref", "HEAD")
                outcome["observed_sha"] = _out(item["repository"]["path"], "rev-parse", "HEAD")
            except (SyncError, UnicodeError, OSError):
                outcome["observation"] = "unavailable"
    return report
