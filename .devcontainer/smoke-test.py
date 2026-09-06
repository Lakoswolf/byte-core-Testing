"""Exercise a candidate in newly created, disposable fictional test roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPOSITORY = Path(__file__).resolve().parents[1]


def run(arguments: list[str], *, expected: int = 0) -> str:
    result = subprocess.run(
        arguments, cwd=REPOSITORY, text=True, capture_output=True, check=False
    )
    if result.returncode != expected:
        raise RuntimeError("command did not return the expected exit status")
    return result.stdout


def digest_files(root: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.iterdir()
        if path.is_file()
    }


def main() -> int:
    # Check before creating test state; unsupported hosts must not be bypassed.
    check = json.loads(run([
        str(REPOSITORY / "bin/byte"), "check", "--format", "json",
    ]))
    if not check["supported"]:
        raise RuntimeError("a supported test target is required")
    root = Path(tempfile.mkdtemp(prefix="byte-container-smoke-")).resolve()
    stage = "candidate construction"
    try:
        artifact = root / "artifact"
        run([
            sys.executable, "scripts/build_release_artifact.py",
            "--version", "0.1.0", "--output", str(artifact),
        ])
        gate = [
            sys.executable, "scripts/check_v01_release.py",
            "--artifact", str(artifact),
            "--evidence", "release/v0.1/manual-evidence.json",
        ]
        run(gate)
        archive = root / "candidate.tar.gz"
        run([
            sys.executable, "scripts/package_release_candidate.py",
            "--artifact", str(artifact), "--output", str(archive),
        ])
        extracted = root / "extracted"
        extracted.mkdir()
        run(["tar", "-xzf", str(archive), "-C", str(extracted)])
        candidate = extracted / "byte-core-0.1.0"
        byte = str(candidate / "bin/byte")
        run([byte, "check"])
        print("PASS: candidate build, integrity/privacy gate, archive, and launcher")

        stage = "packaged helper configuration and shell assets"
        helper_config = root / "helpers.toml"
        helper_config.write_text(run([byte, "helpers", "config", "example"]), encoding="utf-8")
        run([byte, "helpers", "--config", str(helper_config), "config", "validate"])
        for shell in ("bash", "zsh"):
            help_text = run([
                "env", f"BYTE_CORE_HELPERS_CONFIG={helper_config}", shell, "-c",
                '. "$1"; bytehelp; _byte_helpers config validate',
                "byte-helper-smoke", str(candidate / "shell/byte-shell.sh"),
            ])
            if "wakelan" not in help_text or "Helper configuration valid." not in help_text:
                raise RuntimeError("packaged helper assets did not load")
        print("PASS: packaged helper template, validation, and Bash/Zsh dispatch")

        def plan(name: str, arguments: list[str]) -> Path:
            path = root / f"{name}.json"
            path.write_text(run([byte, *arguments]), encoding="utf-8")
            path.chmod(0o600)
            return path

        def result(arguments: list[str], code: str) -> None:
            payload = json.loads(run([byte, *arguments, "--format", "json"]))
            if payload["code"] != code:
                raise RuntimeError("command did not report the expected result")

        stage = "initialization"
        deployment = root / "deployment"
        initial = plan("init-plan", [
            "plan", "init", "--deployment-root", str(deployment),
        ])
        result(["apply", "--plan", str(initial)], "initialized")
        result(["verify", "--plan", str(initial)], "verified")
        result(["apply", "--plan", str(initial)], "already_initialized")
        with (deployment / "notebook.md").open("a", encoding="utf-8") as stream:
            stream.write("\nFictional container-test sentinel: preserve this note.\n")
        before = digest_files(deployment)
        print("PASS: initialization, verification, and exact replay")

        stage = "Core installation"
        core = root / "core"
        state = root / "state"
        install = plan("install-plan", [
            "plan", "install", "--artifact-root", str(candidate),
            "--core-root", str(core), "--state-root", str(state),
            "--core-version", "0.1.0",
        ])
        result(["apply", "--plan", str(install)], "installed")
        result(["verify", "--plan", str(install)], "verified")
        result(["apply", "--plan", str(install)], "already_installed")
        print("PASS: Core installation, verification, and exact replay")

        stage = "shell integration"
        for shell, profile_name in (("bash", ".bashrc"), ("zsh", ".zshrc")):
            home = root / f"{shell}-home"
            home.mkdir()
            profile = home / profile_name
            original = b"# Fictional profile content; preserve these bytes.\n"
            profile.write_bytes(original)
            integration = plan(f"{shell}-plan", [
                "shell", "plan", "--home-root", str(home), "--shell", shell,
                "--shell-script", str(candidate / "shell/byte-shell.sh"),
            ])
            result(["shell", "apply", "--plan", str(integration)], "integrated")
            result(["shell", "verify", "--plan", str(integration)], "verified")
            result(
                ["shell", "apply", "--plan", str(integration)],
                "already_integrated",
            )
            output = run([
                shell, "-c", '. "$1"; byte_status', "byte-smoke", str(profile),
            ])
            if output.strip() != "Byte shell integration is active.":
                raise RuntimeError("shell helper did not report integration")
            removal = plan(f"{shell}-remove-plan", [
                "shell", "plan-remove", "--home-root", str(home), "--shell", shell,
            ])
            result(["shell", "remove", "--plan", str(removal)], "removed")
            result(["shell", "verify", "--plan", str(removal)], "verified")
            if profile.read_bytes() != original:
                raise RuntimeError("fictional profile content changed")
        print("PASS: Bash/Zsh integration, helpers, replay, removal, and preservation")

        stage = "Core removal and preservation"
        removal = plan("remove-plan", [
            "plan", "remove", "--manifest", str(state / "installation.json"),
            "--preserve-root", str(deployment),
        ])
        result(["apply", "--plan", str(removal)], "removed")
        result(["verify", "--plan", str(removal)], "verified")
        result(["apply", "--plan", str(removal)], "already_removed")
        if core.exists() or state.exists() or digest_files(deployment) != before:
            raise RuntimeError("removal or fictional deployment preservation failed")
        print("PASS: Core removal, verification, replay, and deployment preservation")
    except Exception:
        print(
            f"FAIL: {stage}; disposable test state retained at {root}",
            file=sys.stderr,
        )
        return 1
    # Only this invocation's fresh fictional tree is discarded after verification.
    shutil.rmtree(root)
    print("PASS: disposable test state cleaned up; no release evidence was recorded")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, KeyError):
        print(
            "FAIL: prerequisites; run ./bin/byte check for the bounded result",
            file=sys.stderr,
        )
        raise SystemExit(1)
