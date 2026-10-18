"""CLI for offline, explicitly approved helper configuration setup."""

from __future__ import annotations

from . import helper_setup
from .helpers_config import HelperConfigError
from .inventory_io import InventoryError, encode, read_json


def add_parser(commands) -> None:
    parser = commands.add_parser("setup", help="check and prepare standalone helper settings")
    actions = parser.add_subparsers(dest="setup_action", required=True)
    check = actions.add_parser("check", help="check selected settings without running applications")
    check.add_argument("--settings", required=True)
    plan = actions.add_parser("plan", help="plan a new deployment-owned helpers file")
    plan.add_argument("--settings", required=True)
    plan.add_argument("--output", required=True)
    plan.add_argument("--home-root")
    plan.add_argument("--shell", choices=("bash", "zsh"))
    plan.add_argument("--shell-script")
    for name in ("apply", "verify"):
        action = actions.add_parser(name)
        action.add_argument("--plan", required=True)
        if name == "apply":
            action.add_argument("--approve", required=True, help="exact reviewed plan ID")


def run(arguments, output, errors, readiness=None) -> int:
    try:
        action = arguments.setup_action
        if action == "check":
            result = helper_setup.check(arguments.settings)
        elif action == "plan":
            result = helper_setup.build_plan(arguments.settings, arguments.output,
                                            home_root=arguments.home_root, shell=arguments.shell,
                                            shell_script=arguments.shell_script)
        elif action == "apply":
            result = helper_setup.apply(read_json(arguments.plan), arguments.approve)
        else:
            result = helper_setup.verify(read_json(arguments.plan))
        output.write(encode(result).decode())
        return 4 if action == "check" and not result["ready"] else 0
    except (helper_setup.SetupError, HelperConfigError, InventoryError) as error:
        errors.write(f"byte: {error}\n")
        if str(error) in {"setup_not_approved", "setup_plan_stale", "setup_settings_changed",
                          "setup_target_exists", "inventory_target_exists", "inventory_output_in_repository",
                          "inventory_path_invalid"}:
            return 5
        if str(error) == "setup_verification_failed":
            return 6
        if str(error) == "setup_recovery_required":
            return 7
        if str(error) == "setup_write_failed":
            return 70
        return 4
    except OSError:
        errors.write("byte: setup_filesystem_unavailable\n")
        return 4
