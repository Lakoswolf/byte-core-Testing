"""Review, install, and initialize an experimental local Byte Core candidate."""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def check_launcher_readiness() -> int:
    """Check the same shell/PATH runtime chain the installed launcher uses."""
    try:
        result = subprocess.run(
            [str(REPOSITORY_ROOT / "bin" / "byte"), "check"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=15, check=False,
        )
        ready = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ready = False
    if not ready:
        print("Launcher prerequisite check failed. Ensure python3 on PATH is Python "
              "3.11–3.14 with tomllib, Git is available, and the checkout's bin/byte "
              "is executable through /bin/sh. Run ./bin/byte check from the checkout "
              "to inspect host support and prerequisites. Selecting a versioned "
              "Python for this script alone does not select the launcher's python3. "
              "See docs/installation.md#prerequisites. No setup plans were applied.",
              file=sys.stderr)
        return 3
    print("Launcher prerequisite check: passed (python3 and Git on PATH; supported host).")
    return 0


def selected_path(value: str, *, existing: bool = False) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be absolute and contain no parent traversal")
    if ".git" in path.parts:
        raise ValueError("selected paths must be outside Git metadata")
    if path.is_symlink():
        raise ValueError("selected paths must not be symbolic links")
    if existing:
        result = path.resolve(strict=True)
        if not result.is_dir():
            raise ValueError("work parent must be an existing directory")
    else:
        if path.exists():
            raise ValueError("Core, state, and deployment roots must be absent")
        result = path.parent.resolve(strict=True) / path.name
        if not result.parent.is_dir():
            raise ValueError("target parents must be existing directories")
    if result == REPOSITORY_ROOT or REPOSITORY_ROOT in result.parents:
        raise ValueError("all selected paths must be outside the source checkout")
    if result in REPOSITORY_ROOT.parents:
        raise ValueError("selected paths must not contain the source checkout")
    if ".git" in result.parts:
        raise ValueError("selected paths must be outside Git metadata")
    return result


def run(args, cli, build) -> int:
    """Use existing Core commands; retain artifacts and plans on every exit."""
    roots = [selected_path(value) for value in
             (args.core_root, args.state_root, args.deployment_root)]
    parent = selected_path(args.work_parent, existing=True)
    for index, root in enumerate(roots):
        for other in roots[index + 1:]:
            if root == other or root in other.parents or other in root.parents:
                raise ValueError("Core, state, and deployment roots must not overlap")
        if root == parent or root in parent.parents:
            raise ValueError("work parent must be outside the new target roots")
    status = cli.main(["check"])
    if status:
        return status
    status = check_launcher_readiness()
    if status:
        return status
    work = Path(tempfile.mkdtemp(prefix="byte-setup-", dir=parent))
    print(f"Private preparation directory (preserved): {work}", flush=True)
    artifact = build(args.version, work / "artifact")
    commands = [
        ("install", ["plan", "install", "--artifact-root", str(artifact),
                     "--core-root", str(roots[0]), "--state-root", str(roots[1]),
                     "--core-version", args.version]),
        ("init", ["plan", "init", "--deployment-root", str(roots[2])]),
    ]
    plans = []
    for name, command in commands:
        output = io.StringIO()
        status = cli.main(command, stdout=output)
        if status:
            print(output.getvalue())
            return status
        content = output.getvalue()
        plan_id = json.loads(content)["plan_id"]
        path = work / f"{name}-plan.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        plans.append((name, path, plan_id, content))
        print(f"\n{name} plan saved at {path}:\n{content}")
    print("Review both plans and their backout actions. Installation is pre-alpha.\n"
          "If initialization fails after installation, the installed Core remains.\n"
          "No combined automatic rollback or deletion of deployment files occurs.\n"
          "Keep the plans and artifact for verification and reviewed recovery.")
    if args.plan_only:
        print("Plans prepared; nothing installed or initialized.")
        return 0
    for name, path, plan_id, content in plans:
        try:
            approved = input(f"Type the full {name} plan ID to approve (anything else cancels): ")
        except EOFError:
            approved = ""
        if approved != plan_id:
            print("Setup cancelled; preparation files retained; no plans applied.")
            return 5
    status = check_launcher_readiness()
    if status:
        return status
    # Refuse a plan replacement during review before applying either operation.
    for name, path, plan_id, content in plans:
        if path.is_symlink() or path.read_bytes() != content.encode("utf-8"):
            raise ValueError("saved plan changed during review; no plans applied")
    for name, path, plan_id, content in plans:
        for operation in ("apply", "verify"):
            if path.is_symlink() or path.read_bytes() != content.encode("utf-8"):
                raise ValueError("saved plan changed; preserve state and review before continuing")
            status = cli.main([operation, "--plan", str(path)])
            if status:
                print(f"Stopped during {name} {operation}. Preserve all remaining state "
                      "and review the saved plans before recovery.")
                return status
    print(f"Experimental Core installation and starter deployment verified.\n"
          f"Installed launcher: {roots[0] / 'releases' / args.version / 'bin/byte'}\n"
          f"Deployment: {roots[2]}\n"
          "deployment.toml: schema-1 configuration.\n"
          "manifest.md: declared components and relationships.\n"
          "runbook.md: reviewed operating and recovery procedures.\n"
          "audit-log.md: completed changes and validation evidence.\n"
          "notebook.md: lessons and unresolved questions.\n"
          "The launcher requires Python 3.11–3.14 as python3 on PATH.\n"
          "Read starter files before editing; edits invalidate the original init verification.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="local candidate version with release notes")
    parser.add_argument("--core-root", required=True, help="new absolute Core root")
    parser.add_argument("--state-root", required=True, help="new absolute installation-state root")
    parser.add_argument("--deployment-root", required=True, help="new absolute starter deployment root")
    parser.add_argument("--work-parent", required=True, help="existing absolute private preparation parent")
    parser.add_argument("--plan-only", action="store_true", help="build artifact and save plans without applying")
    args = parser.parse_args(argv)
    if not (3, 11) <= sys.version_info[:2] <= (3, 14):
        print("Setup requires Python 3.11–3.14. Run this script with an installed "
              "interpreter in that range; no packages were installed.", file=sys.stderr)
        return 3
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
    sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
    from byte_core import cli
    from build_release_artifact import BuildError, build
    try:
        return run(args, cli, build)
    except (ValueError, OSError, RuntimeError, BuildError) as error:
        print(f"Setup stopped: {error}. Preserve any preparation files and partial "
              "state; no automatic cleanup was attempted by this wrapper.", file=sys.stderr)
        return 5
    except KeyboardInterrupt:
        print("Setup interrupted. Preserve plans and partial state for review.", file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())
