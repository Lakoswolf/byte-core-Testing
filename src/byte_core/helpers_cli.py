"""Experimental helper dispatch; plans never imply operational approval."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from . import helpers_config
from .inventory_io import InventoryError, read_json


def add_parser(commands) -> None:
    parser = commands.add_parser("helpers", help="configure and run optional shell helpers")
    parser.add_argument("--config", help="explicit absolute helpers TOML file; overrides BYTE_CORE_HELPERS_CONFIG")
    actions = parser.add_subparsers(dest="helper", required=True)
    config = actions.add_parser("config", help="inspect helper configuration without executing it")
    modes = config.add_subparsers(dest="helper_config_action", required=True)
    modes.add_parser("validate")
    modes.add_parser("example", help="print the generic starter TOML")
    get = modes.add_parser("get")
    get.add_argument("key")
    prompt = actions.add_parser("prompt", help="render optional local prompt data")
    prompt.add_argument("--shell", choices=("bash", "zsh"), default="bash")
    assistant = actions.add_parser("assistant")
    assistant.add_argument("mode", choices=("new", "resume"))
    assistant.add_argument("extra", nargs=argparse.REMAINDER)
    status = actions.add_parser("git-status")
    status.add_argument("extra", nargs=argparse.REMAINDER)
    for helper, run_name in (("canisync", "apply"), ("labstatus", "run"), ("wakelan", "run")):
        item = actions.add_parser(helper)
        operations = item.add_subparsers(dest="helper_operation", required=True)
        plan = operations.add_parser("plan", help="print an offline JSON plan")
        if helper == "labstatus":
            plan.add_argument("--device", action="append", required=True)
        elif helper == "wakelan":
            plan.add_argument("--device", required=True)
        apply = operations.add_parser(run_name, help="execute an exact reviewed plan")
        apply.add_argument("--plan", required=True)
        apply.add_argument("--approve", required=True, help="full reviewed plan ID")


def _extra(values: list[str]) -> list[str]:
    return values[1:] if values[:1] == ["--"] else values


def run(arguments, output, errors, readiness=None) -> int:
    from . import helper_network, helper_shell, helper_sync

    try:
        if arguments.helper == "config" and arguments.helper_config_action == "example":
            output.write((Path(__file__).resolve().parents[2] / "templates" / "helpers.toml").read_text())
            return 0
        config_path = arguments.config if arguments.config is not None else os.environ.get("BYTE_CORE_HELPERS_CONFIG") or None
        config = helpers_config.load(config_path)
        if arguments.helper == "config":
            if arguments.helper_config_action == "get":
                output.write(helpers_config.get_scalar(config, arguments.key) + "\n")
            else:
                output.write("Helper configuration valid. No applications or network operations were started.\n")
            return 0
        if arguments.helper == "assistant":
            return helper_shell.run_assistant(config, arguments.mode, _extra(arguments.extra))
        if arguments.helper == "prompt":
            output.write(helper_shell.prompt_text(config, arguments.shell))
            return 0
        if arguments.helper == "git-status":
            return helper_shell.git_status(_extra(arguments.extra))
        helper = arguments.helper
        if arguments.helper_operation == "plan":
            if helper == "canisync":
                result = helper_sync.plan(config)
            elif helper == "labstatus":
                result = helper_network.plan_status(config, arguments.device)
            else:
                result = helper_network.plan_wake(config, arguments.device)
        else:
            plan = read_json(arguments.plan)
            if helper == "canisync":
                result = helper_sync.apply(config, plan, arguments.approve)
            elif helper == "labstatus":
                result = helper_network.run_status(config, plan, arguments.approve)
            else:
                result = helper_network.run_wake(config, plan, arguments.approve)
        output.write(json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=2) + "\n")
        if helper == "canisync":
            if result.get("status") == "partial":
                return 7
            if result.get("status") == "failed":
                return 5
        if result.get("kind") == "wakelan_result":
            return {"unavailable": 3, "error": 70, "unknown": 7}.get(result.get("status"), 0)
        if result.get("kind") == "labstatus_result":
            states = {address["status"] for device in result["devices"] for address in device["addresses"]}
            if "error" in states:
                return 70
            if "unavailable" in states:
                return 3
        return 0
    except (helpers_config.HelperConfigError, helper_network.NetworkHelperError,
            helper_sync.SyncError, helper_shell.ShellHelperError) as error:
        errors.write(f"byte: {error}\n")
        return 4
    except InventoryError:
        errors.write("byte: cannot read helper plan: use an absolute regular JSON file without symlinks\n")
        return 4
    except OSError:
        errors.write("byte: helper prerequisite or local input unavailable\n")
        return 3


def main(argv=None) -> int:
    # Retain the same parser and host gate as the main launcher.
    from .cli import main as byte_main
    return byte_main(["helpers", *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    raise SystemExit(main())
