"""CLI wiring for optional inventory setup; no implicit network operations."""

from __future__ import annotations

from . import discovery, inventory
from .inventory_io import InventoryError, encode, read_json


def add_parser(commands) -> None:
    parser = commands.add_parser("inventory", help="plan discovery and review a device catalog")
    actions = parser.add_subparsers(dest="inventory_action", required=True)
    plan = actions.add_parser("plan", help="plan bounded discovery or service inspection")
    plan.add_argument("--network", required=True)
    plan.add_argument("--output", required=True)
    plan.add_argument("--mode", choices=("discover", "inspect"), default="discover")
    plan.add_argument("--target", action="append", default=[])
    for name in ("scan", "import", "apply"):
        action = actions.add_parser(name)
        action.add_argument("--plan", required=True)
        action.add_argument("--approve", required=True, help="exact reviewed plan ID")
        action.add_argument("--format", choices=("text", "json"), default="text")
        if name == "import":
            action.add_argument("--xml", required=True)
    review = actions.add_parser("plan-catalog", help="plan a reviewed inventory snapshot")
    review.add_argument("--observations", required=True)
    review.add_argument("--selection", required=True)
    review.add_argument("--output", required=True)
    review.add_argument("--capabilities")
    review.add_argument("--previous")
    lookup = actions.add_parser("lookup", help="look up an exact model in a cited local catalog")
    lookup.add_argument("--capabilities", required=True)
    lookup.add_argument("--manufacturer", required=True)
    lookup.add_argument("--model", required=True)
    check = actions.add_parser("verify")
    check.add_argument("--plan", required=True)
    check.add_argument("--format", choices=("text", "json"), default="text")


def run(arguments, output, errors, readiness) -> int:
    try:
        action = arguments.inventory_action
        if action == "lookup":
            matches = inventory.lookup_capabilities(
                read_json(arguments.capabilities), arguments.manufacturer, arguments.model)
            output.write(encode({"capabilities": matches}).decode())
            return 0
        if action == "plan":
            plan = discovery.build_scan_plan(arguments.network, arguments.output,
                                             mode=arguments.mode, targets=arguments.target)
            output.write(encode(plan).decode())
            return 0
        if action == "plan-catalog":
            plan = inventory.build_catalog_plan(
                arguments.observations, arguments.selection, arguments.output,
                catalog_file=arguments.capabilities, previous_file=arguments.previous)
            output.write(encode(plan).decode())
            return 0
        plan = read_json(arguments.plan)
        if action in {"scan", "import"}:
            value = discovery.scan(plan, arguments.approve,
                                   xml_file=arguments.xml if action == "import" else None)
            result = {"code": "observations_saved", "plan_id": plan["id"],
                      "devices": len(value["hosts"]), "source": value["source"]}
        elif action == "apply":
            value = inventory.apply_catalog(plan, arguments.approve)
            result = {"code": "inventory_saved", "plan_id": plan["id"],
                      "devices": len(value["devices"])}
        else:
            inventory.verify(plan)
            result = {"code": "verified", "plan_id": plan["id"]}
        if arguments.format == "json":
            output.write(encode(result).decode())
        else:
            output.write(f"Result: {result['code']}\nPlan ID: {result['plan_id']}\n")
            if "devices" in result:
                output.write(f"Devices: {result['devices']}\n")
            if "source" in result:
                output.write(f"Source: {result['source']}\n")
        return 0
    except InventoryError as error:
        errors.write(f"byte: {error.code}\n")
        if error.code in {"nmap_unavailable"}:
            return 3
        if error.code in {"inventory_not_approved", "inventory_target_exists",
                          "inventory_output_in_repository", "inventory_path_invalid",
                          "inventory_plan_stale"}:
            return 5
        if error.code == "inventory_verification_failed":
            return 6
        if error.code == "inventory_recovery_required":
            return 7
        if error.code in {"inventory_scan_failed", "inventory_scan_timeout",
                          "inventory_scan_output_limit", "inventory_write_failed"}:
            return 70
        return 4
