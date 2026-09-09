"""Review, install, and initialize an experimental local Byte Core candidate."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOSITORY = "Lakoswolf/byte-core-Testing"


def repository_url(value: str) -> str:
    """Accept a GitHub repository identity, never credentials or a command URL."""
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*", value) is None:
        raise ValueError("repository must be OWNER/NAME on github.com, without a URL or credentials")
    return f"https://github.com/{value}.git"


def repository_ref(value: str) -> str:
    if (re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", value) is None
            or any(part in {"", ".", ".."} or part.endswith((".lock", "."))
                   or part.startswith(".") for part in value.split("/"))
            or ".." in value):
        raise ValueError("use HEAD, a branch, a tag, or a full commit SHA for --ref")
    return value


def source_git(source: Path, *arguments: str) -> str:
    """Run bounded Git operations without shell evaluation or terminal credentials."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    try:
        result = subprocess.run(
            ["git", "-c", "core.hooksPath=" + os.devnull,
             "-c", "protocol.file.allow=never", "-c", "protocol.ext.allow=never",
             "-c", "submodule.recurse=false", "-C", str(source), *arguments],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=300, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Git could not complete the download/check. The source folder is retained.") from error
    if result.returncode:
        raise RuntimeError("Git failed. Check repository access, the selected ref, network, and existing Git credentials. "
                           "The source folder is retained; no setup was started.")
    return result.stdout.strip()


def verify_source(source: Path, commit: str):
    if source_git(source, "rev-parse", "HEAD") != commit:
        raise ValueError("downloaded source revision changed; setup stopped")
    if source_git(source, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("downloaded source has local changes; setup stopped")
    for name in ("src", "src/byte_core", "scripts", "bin", "docs", "docs/release-notes"):
        path = source / name
        if path.is_symlink() or not path.is_dir():
            raise ValueError("selected revision does not contain the expected Byte Core source layout")
    for name in ("src/byte_core/__init__.py", "src/byte_core/cli.py",
                 "scripts/build_release_artifact.py", "bin/byte"):
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("selected revision does not contain the expected Byte Core source layout")


def download_source(args):
    """Download and identify source; ask separately before using its Python code."""
    repository = args.repository or DEFAULT_REPOSITORY
    url = repository_url(repository)
    ref = repository_ref(args.ref or "HEAD")
    if shutil.which("git") is None:
        raise RuntimeError("Downloading source requires Git on PATH. Install/configure Git separately and retry.")
    print(f"\nDownload Byte Core source\nRepository: {url}\nRequested ref: {ref}\n"
          "HEAD means the repository's current default branch.\n"
          "This creates a fresh source folder; existing checkouts are preserved.")
    parent = prompt_path("Existing parent for the download", args.source_parent or Path.home(), existing=True)
    print(f"Download destination: a new private byte-source-* folder under {parent}")
    if not yes_no("Download this repository revision?"):
        raise SetupCancelled
    work = Path(tempfile.mkdtemp(prefix="byte-source-", dir=parent))
    source = work / "checkout"
    source.mkdir(mode=0o700)
    print(f"Source folder (preserved): {source}", flush=True)
    source_git(source, "init", "--quiet")
    source_git(source, "remote", "add", "origin", url)
    source_git(source, "fetch", "--quiet", "--depth=1", "--no-tags", "--no-recurse-submodules", "origin", ref)
    commit = source_git(source, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("Git did not return a full source commit SHA")
    source_git(source, "checkout", "--quiet", "--detach", commit)
    verify_source(source, commit)
    record = work / "source.json"
    descriptor = os.open(record, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"repository": repository, "requested_ref": ref, "commit": commit}, stream, indent=2)
        stream.write("\n")
    print(f"Downloaded commit: {commit}\nSource record: {record}\n"
          "Setup uses this exact checkout. A commit ID identifies the source; it is not release certification.")
    if args.download_only:
        print("Download complete. No downloaded Python code was run; source files are retained for review.")
        return None
    if not yes_no("Use this downloaded revision's code to continue setup?"):
        raise SetupCancelled
    verify_source(source, commit)
    return source


class SetupCancelled(Exception):
    """The operator cancelled or input ended; never interpret that as approval."""


def answer(prompt: str) -> str:
    try:
        value = input(prompt).strip()
    except EOFError as error:
        raise SetupCancelled from error
    if value.lower() in {"q", "quit", "cancel"}:
        raise SetupCancelled
    return value


def yes_no(question: str, *, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        value = answer(question + suffix).lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter yes or no (or q to cancel).")


def prompt_path(label: str, default=None, *, existing=False) -> str:
    while True:
        hint = f" [{default}]" if default is not None else ""
        value = answer(f"{label}{hint}: ") or (str(default) if default is not None else "")
        try:
            return str(selected_path(value, existing=existing))
        except (ValueError, OSError) as error:
            print(f"Choose another absolute path: {error}")


def local_versions() -> list[str]:
    versions = [path.stem[1:] for path in (REPOSITORY_ROOT / "docs/release-notes").glob("v*.md")
                if not path.is_symlink()
                and re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", path.stem)]
    return sorted(versions, key=lambda version: tuple(map(int, version.split("."))))


def guide(args):
    """Collect explicit choices without creating directories or changing settings."""
    print("\nByte Core guided setup\n"
          "Install an experimental candidate from this source checkout.\n"
          "You choose the locations and review saved plans before installation.\n"
          "Existing installations are preserved; this wizard creates a new installation.\n"
          "Python 3.11+ and the POSIX lifecycle backend are required.\n"
          "Enter q to cancel at any question.\n")
    if not yes_no("Continue with experimental setup?"):
        raise SetupCancelled
    versions = local_versions()
    if not versions:
        raise ValueError("no local candidate release notes found")
    if args.version is None:
        proposed = versions[-1]
        print("Available local candidate labels: " + ", ".join(versions))
        if yes_no(f"Use candidate version {proposed}?", default=True):
            args.version = proposed
        else:
            while args.version not in versions:
                args.version = answer("Candidate version from the list: ")
                if args.version not in versions:
                    print("Choose a version with local release notes.")
    if args.version not in versions:
        raise ValueError("selected version has no local release notes")
    if not args.skip_init and args.deployment_root is None:
        args.skip_init = not yes_no("Create starter deployment documents too?", default=True)
    print("\nChoose an existing folder for private preparation files.\n"
          "Suggested installation folders will be new children of that folder.\n"
          "Paths are literal absolute paths; do not use ~ or shell variables.")
    args.work_parent = prompt_path("Preparation parent", args.work_parent or Path.home(), existing=True)
    parent = Path(args.work_parent)
    fields = [("core_root", "Core program files", "byte-core"),
              ("state_root", "Installation state", "byte-core-state")]
    if not args.skip_init:
        fields.append(("deployment_root", "Your starter documents", "byte-core-deployment"))
    while True:
        suggestions = {field: getattr(args, field) or str(parent / child)
                       for field, _, child in fields}
        print("\nProposed locations:")
        for field, label, _ in fields:
            print(f"  {label}: {suggestions[field]}")
        suggested = yes_no("Use these locations?", default=True)
        for field, label, _ in fields:
            if suggested:
                try:
                    value = str(selected_path(suggestions[field]))
                except (ValueError, OSError) as error:
                    print(f"{label}: {error}; existing files will be preserved.")
                    value = prompt_path(label)
            else:
                value = prompt_path(label, suggestions[field])
            setattr(args, field, value)
        try:
            validate_paths(args)
            break
        except ValueError as error:
            print(f"Please revise the locations: {error}")
    if not args.plan_only:
        args.plan_only = yes_no("Only prepare plans for review now (skip installation)?", default=True)
    print(f"\nCandidate: {args.version}\nMode: " + ("prepare plans only" if args.plan_only else "review and install"))
    if not yes_no("Check prerequisites and prepare the selected plans?"):
        raise SetupCancelled
    return args


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
              "3.11+ with tomllib and the checkout's bin/byte "
              "is executable through /bin/sh. Run ./bin/byte check from the checkout "
              "to inspect lifecycle prerequisites. Selecting a versioned "
              "Python for this script alone does not select the launcher's python3. "
              "See docs/installation.md#prerequisites. No setup plans were applied.",
              file=sys.stderr)
        return 3
    print("Launcher prerequisite check: passed (launcher Python and POSIX lifecycle prerequisites).")
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
    if (REPOSITORY_ROOT / "src/byte_core/cli.py").is_file():
        if result == REPOSITORY_ROOT or REPOSITORY_ROOT in result.parents:
            raise ValueError("all selected paths must be outside the source checkout")
        if not existing and result in REPOSITORY_ROOT.parents:
            raise ValueError("selected paths must not contain the source checkout")
    if ".git" in result.parts:
        raise ValueError("selected paths must be outside Git metadata")
    return result


def validate_paths(args):
    values = [args.core_root, args.state_root]
    if not getattr(args, "skip_init", False):
        values.append(args.deployment_root)
    roots = [selected_path(value) for value in values]
    parent = selected_path(args.work_parent, existing=True)
    for index, root in enumerate(roots):
        for other in roots[index + 1:]:
            if root == other or root in other.parents or other in root.parents:
                raise ValueError("Core, state, and deployment roots must not overlap")
        if root == parent or root in parent.parents:
            raise ValueError("work parent must be outside the new target roots")
    return roots, parent


def save_private(path: Path, content: str):
    """Exclusively publish a new private file through its selected parent."""
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        descriptor = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(parent)


def selected_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path.is_symlink() or not path.is_file():
        raise ValueError("select an existing absolute regular file without symlinks or parent traversal")
    return path.resolve(strict=True)


def prompt_file(label: str) -> Path:
    while True:
        try:
            return selected_file(answer(label + ": "))
        except (OSError, ValueError) as error:
            print(error)


def literal_arguments(label: str) -> list[str]:
    while True:
        value = answer(label + " as a JSON array ([] for none): ")
        try:
            result = json.loads(value)
            if isinstance(result, list) and all(isinstance(item, str) for item in result):
                return result
        except ValueError:
            pass
        print('Enter an array of literal strings, for example ["--project", "{project}"].')


def helper_choices() -> str:
    values = {key: yes_no(question) for key, question in (
        ("prompt", "Enable the optional Byte prompt?"),
        ("history", "Enable prefix-history search?"),
        ("aliases", "Enable convenience aliases (ll, la, ..)?"),
    )}
    lines = ["# Deployment-owned Byte helper settings; edit as data, never source as shell code.",
             "schema_version = 1", "", "[shell]"]
    lines.extend(f"{key} = {str(value).lower()}" for key, value in values.items())
    lines.append("highlighting = false")
    if yes_no("Configure a development-directory shortcut?"):
        directory = prompt_path("Existing development directory", existing=True)
        lines.append("development_directory = " + json.dumps(directory, ensure_ascii=False))
    if yes_no("Configure an assistant application for byten and byter?"):
        executable = answer("Application executable (name on PATH or absolute path): ")
        lines.extend(["", "[assistant]", "executable = " + json.dumps(executable, ensure_ascii=False)])
        for key, label in (("new_args", "New-session arguments"), ("resume_args", "Resume arguments")):
            lines.append(key + " = " + json.dumps(literal_arguments(label), ensure_ascii=False))
    return "\n".join(lines) + "\n"


def session_script(release: Path, helpers: Path | None) -> str:
    directory = str(release / "bin")
    if ":" in directory or any(ord(char) < 32 for char in directory):
        raise ValueError("shell PATH integration requires a bin path without colons or control characters")
    lines = ["# Deployment-owned Byte session entrypoint; review before sourcing."]
    if helpers is not None:
        lines.append("export BYTE_CORE_HELPERS_CONFIG=" + shlex.quote(str(helpers)))
    quoted = shlex.quote(directory)
    lines.extend([f'case ":${{PATH-}}:" in *:{quoted}:*) ;;',
                  f'  *) export PATH={quoted}${{PATH:+":$PATH"}} ;; esac',
                  ". " + shlex.quote(str(release / "shell/byte-shell.sh"))])
    return "\n".join(lines) + "\n"


def extra_plan(cli, command, path: Path, *, family: str, plan_only: bool):
    output = io.StringIO()
    status = cli.main(command, stdout=output)
    if status:
        print(output.getvalue())
        return status
    content = output.getvalue()
    plan = json.loads(content)
    plan_id = plan["id" if family == "setup" else "plan_id"]
    save_private(path, content)
    print(f"\nReview the {family} plan saved at {path}:\n{content}")
    apply = [family, "apply", "--plan", str(path)]
    if family == "setup":
        apply.extend(["--approve", plan_id])
    if plan_only:
        launcher = str(REPOSITORY_ROOT / "bin/byte")
        print("Prepared only. After review:\n  " + shlex.join([launcher, *apply]) +
              "\n  " + shlex.join([launcher, family, "verify", "--plan", str(path)]))
        return 0
    if answer(f"Type the full {family} plan ID to apply (anything else cancels): ") != plan_id:
        raise SetupCancelled
    if path.is_symlink() or path.read_bytes() != content.encode("utf-8"):
        raise ValueError("saved optional-setup plan changed; no apply attempted")
    status = cli.main(apply)
    if status:
        return status
    return cli.main([family, "verify", "--plan", str(path)])


def finish_setup(install_plan: str, cli, *, plan_only=False, deployment=None, starter_plan=None) -> int:
    """Configure optional settings/profile integration for one verified installation."""
    plan_path = selected_file(install_plan)
    if plan_path.stat().st_size > 1024 * 1024:
        raise ValueError("installation plan is too large")
    plan_bytes = plan_path.read_bytes()
    data = json.loads(plan_bytes)
    if not isinstance(data, dict) or data.get("operation") != "install":
        raise ValueError("--finish-setup requires a saved installation plan")
    status = cli.main(["verify", "--plan", str(plan_path)])
    if status:
        return status
    if plan_path.is_symlink() or plan_path.read_bytes() != plan_bytes:
        raise ValueError("installation plan changed during verification")
    if starter_plan is not None:
        starter = selected_file(starter_plan)
        status = cli.main(["verify", "--plan", str(starter)])
        if status:
            return status
        starter_data = json.loads(starter.read_text())
        if starter_data.get("operation") != "init":
            raise ValueError("--starter-plan requires a saved initialization plan")
        deployment = Path(starter_data["deployment_root"])
    release = Path(data["core_root"]) / "releases" / data["manifest"]["core_version"]
    core, state = Path(data["core_root"]), Path(data["state_root"])
    print(f"\nFinish Byte setup\nVerified installation: {release}\n"
          "For everyday use, keep Core, settings, and the session script in permanent locations.\n"
          "This step uses the verified installation as-is; it does not move or replace it.\n"
          "Optional steps are independent. Declining or failing a later step preserves earlier work.")
    if not yes_no("Continue with optional configuration?"):
        return 0
    parent = Path(prompt_path("Existing parent for private configuration plans", plan_path.parent, existing=True))
    work = Path(tempfile.mkdtemp(prefix="byte-config-", dir=parent))
    print(f"Configuration plans (preserved): {work}")

    def outside_installation(path):
        for root in (core, state):
            if path == root or root in path.parents:
                raise ValueError("helper settings and session scripts must remain outside Core and installation state")
        return path

    helpers = None
    if yes_no("Configure optional helper settings?", default=True):
        if yes_no("Use an existing helpers TOML file?"):
            helpers = outside_installation(prompt_file("Existing helpers TOML"))
            status = cli.main(["setup", "check", "--settings", str(helpers)])
        else:
            content = helper_choices()
            helpers = outside_installation(Path(prompt_path("New helper settings file", Path.home() / ".byte-helpers.toml")))
            prepared = work / "prepared-helpers.toml"
            save_private(prepared, content)
            print(f"\nPrepared helper choices:\n{content}")
            status = extra_plan(cli, ["setup", "plan", "--settings", str(prepared), "--output", str(helpers)],
                                work / "helpers-plan.json", family="setup", plan_only=plan_only)
        if status:
            print("Helper configuration stopped; the Core installation remains available.")
            return status
    if yes_no("Add byte and its helpers to a Bash or Zsh profile?"):
        shell = "bash" if yes_no("Use Bash? (No selects Zsh)", default=True) else "zsh"
        if shutil.which(shell) is None:
            raise ValueError(f"{shell} is unavailable; install the selected shell separately")
        status = cli.main(["check"])
        if status:
            return status
        home = str(outside_installation(Path(prompt_path("Home directory whose shell profile may be changed", Path.home(), existing=True))))
        wrapper = outside_installation(Path(prompt_path("New permanent session script", Path.home() / ".byte-session.sh")))
        if wrapper == helpers:
            raise ValueError("helper settings and session script must use different files")
        content = session_script(release, helpers)
        print(f"\nSession script to save at {wrapper}:\n{content}\n"
              "Its profile plan will bind this file. The installed shell assets remain covered by\n"
              "installation verification; this custom entrypoint does not recursively bind imports.")
        if not yes_no("Save this new session script and prepare the profile plan?"):
            raise SetupCancelled
        save_private(wrapper, content)
        status = extra_plan(cli, ["shell", "plan", "--home-root", home, "--shell", shell,
                                  "--shell-script", str(wrapper)],
                            work / "shell-plan.json", family="shell", plan_only=plan_only)
        if status:
            print("Shell configuration stopped. Keep the session script, plans, and profile backups for review.")
            return status
        if not plan_only:
            print(f"Profile verified. Open a new {shell} terminal, then run: command -v byte; byte check; bytehelp\n"
                  "The running parent shell is unchanged. Existing aliases/functions named byte may take precedence.\n"
                  "Profile backups are retained in the selected home's .byte-backups directory.")
    if deployment is not None:
        notebook = Path(deployment) / "notebook.md"
        print(f"\nYour starter documents: {deployment}\n"
              "manifest.md: record only confirmed components. runbook.md: write reviewed procedures.\n"
              "audit-log.md: record completed changes. notebook.md: capture questions and next steps.\n"
              "Editing is expected customization; the original init plan will then report differences.")
        if not plan_only and yes_no("Open the starter notebook in an editor now?"):
            editor = answer("Editor executable (for example nano or vi; no command-line arguments): ")
            executable = shutil.which(editor)
            if executable is None or editor.startswith("-"):
                raise ValueError("selected editor executable is unavailable")
            return subprocess.call([executable, str(notebook)])
    print("Optional setup preparation complete." if plan_only else "Selected optional setup steps verified.")
    return 0


def run(args, cli, build) -> int:
    """Use existing Core commands; retain artifacts and plans on every exit."""
    roots, parent = validate_paths(args)
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
    ]
    if not getattr(args, "skip_init", False):
        commands.append(("init", ["plan", "init", "--deployment-root", str(roots[2])]))
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
        print(f"\n{name} plan saved at {path}\nPlan ID: {plan_id}")
        if not getattr(args, "guided", False):
            print(content)
    if getattr(args, "guided", False) and yes_no("Show the complete saved plans?"):
        for name, path, plan_id, content in plans:
            print(f"\n{name}:\n{content}")
    print("Review the saved plans and their backout actions. Installation is pre-alpha.\n"
          "If initialization fails after installation, the installed Core remains.\n"
          "No combined automatic rollback or deletion of deployment files occurs.\n"
          "Keep the plans and artifact for verification and reviewed recovery.")
    if args.plan_only:
        print("Plans prepared; nothing installed or initialized.\n"
              "Keep the artifact and plans together. Review before applying. Apply install before init.\n"
              "Rerunning this wizard creates new plans; it does not resume these plans.")
        launcher = shlex.quote(str(REPOSITORY_ROOT / "bin/byte"))
        for name, path, plan_id, content in plans:
            print(f"\nAfter reviewing the {name} plan:\n"
                  f"  {launcher} apply --plan {shlex.quote(str(path))}\n"
                  f"  {launcher} verify --plan {shlex.quote(str(path))}")
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
    validate_paths(args)
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
    launcher = roots[0] / 'releases' / args.version / 'bin/byte'
    print(f"Experimental Core installation verified.\nInstalled launcher: {launcher}\n"
          f"Try it: {shlex.quote(str(launcher))} check\n"
          "Use this full launcher path; shell profile setup is a separate step.\n"
          "The launcher requires Python 3.11+ as python3 on PATH.")
    if len(roots) > 2:
        print(f"Starter deployment verified: {roots[2]}\n"
          "deployment.toml: schema-1 configuration.\n"
          "manifest.md: declared components and relationships.\n"
          "runbook.md: reviewed operating and recovery procedures.\n"
          "audit-log.md: completed changes and validation evidence.\n"
          "notebook.md: lessons and unresolved questions.\n"
          "Read starter files before editing; edits invalidate the original init verification.")
    print(f"Next: {roots[0] / 'releases' / args.version / 'docs/getting-started.md'}\n"
          "Optional helper settings and shell integration are documented in docs/setup.md\n"
          "and docs/shell-integration.md beside that guide. Preparation files are retained.")
    install_plan = plans[0][1]
    print("Configure helpers and shell integration later with:\n  " +
          shlex.join([sys.executable, str(Path(__file__).resolve()), "--finish-setup", str(install_plan)]))
    if getattr(args, "guided", False):
        return finish_setup(str(install_plan), cli, deployment=roots[2] if len(roots) > 2 else None)
    return 0


def main(argv=None) -> int:
    global REPOSITORY_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-repo", action="store_true", help="download fresh GitHub source before setup")
    parser.add_argument("--repository", help=f"GitHub OWNER/NAME (default: {DEFAULT_REPOSITORY})")
    parser.add_argument("--ref", help="branch, tag, or full commit SHA (default: remote HEAD)")
    parser.add_argument("--source-parent", help="existing absolute parent for the private source download")
    parser.add_argument("--download-only", action="store_true", help="download source for review without running setup")
    parser.add_argument("--guided", action="store_true", help="ask setup questions even when paths are supplied")
    parser.add_argument("--finish-setup", metavar="INSTALL_PLAN", help="configure helpers/profile for a verified installation without reinstalling")
    parser.add_argument("--starter-plan", metavar="INIT_PLAN", help="verify starter documents and offer notebook onboarding with --finish-setup")
    parser.add_argument("--version", help="local candidate version with release notes")
    parser.add_argument("--core-root", help="new absolute Core root")
    parser.add_argument("--state-root", help="new absolute installation-state root")
    parser.add_argument("--deployment-root", help="new absolute starter deployment root")
    parser.add_argument("--work-parent", help="existing absolute private preparation parent")
    parser.add_argument("--skip-init", action="store_true", help="install Core without creating starter documents")
    parser.add_argument("--plan-only", action="store_true", help="build artifact and save plans without applying")
    args = parser.parse_args(argv)
    if sys.version_info[0] != 3 or sys.version_info[:2] < (3, 11):
        print("Setup requires Python 3.11 or later in the Python 3 series. "
              "Select a compatible interpreter; no packages were installed.", file=sys.stderr)
        return 3
    if args.skip_init and args.deployment_root is not None:
        parser.error("--skip-init cannot be combined with --deployment-root")
    if args.finish_setup and any((args.version, args.core_root, args.state_root, args.deployment_root,
                                 args.skip_init, args.work_parent, args.download_only)):
        parser.error("--finish-setup uses the saved install plan; omit new-installation arguments and --download-only")
    if args.starter_plan and not args.finish_setup:
        parser.error("--starter-plan requires --finish-setup")
    required = ["version", "core_root", "state_root", "work_parent"]
    if not args.skip_init:
        required.append("deployment_root")
    remote = (args.from_repo or args.repository is not None or args.ref is not None
              or args.source_parent is not None or args.download_only
              or not (REPOSITORY_ROOT / "src/byte_core/cli.py").is_file())
    args.guided = args.guided or bool(args.finish_setup) or any(getattr(args, field) is None for field in required)
    if remote and not sys.stdin.isatty():
        parser.error("repository download requires an interactive terminal for source selection and approval")
    if args.guided and not sys.stdin.isatty():
        parser.error("guided setup needs an interactive terminal; provide all paths and --version "
                     "with --plan-only for noninteractive plan preparation")
    sys.dont_write_bytecode = True
    if remote:
        try:
            source = download_source(args)
        except SetupCancelled:
            print("Download/setup cancelled. Any downloaded files are preserved.")
            return 5
        except (ValueError, OSError, RuntimeError) as error:
            print(f"Source preparation stopped: {error}", file=sys.stderr)
            return 5
        except KeyboardInterrupt:
            print("Download interrupted. Preserve any downloaded files for review.", file=sys.stderr)
            return 7
        if source is None:
            return 0
        REPOSITORY_ROOT = source
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
    sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
    from byte_core import cli
    from build_release_artifact import BuildError, build
    try:
        if args.finish_setup:
            return finish_setup(args.finish_setup, cli, plan_only=args.plan_only, starter_plan=args.starter_plan)
        if args.guided:
            args = guide(args)
        return run(args, cli, build)
    except SetupCancelled:
        print("Setup cancelled. Any preparation files are preserved; no further actions will run.")
        return 5
    except (ValueError, OSError, RuntimeError, BuildError) as error:
        print(f"Setup stopped: {error}. Preserve any preparation files and partial "
              "state; no automatic cleanup was attempted by this wrapper.", file=sys.stderr)
        return 5
    except KeyboardInterrupt:
        print("Setup interrupted. Preserve plans and partial state for review.", file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())
