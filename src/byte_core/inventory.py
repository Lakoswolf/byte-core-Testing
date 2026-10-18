"""Review observations into immutable, deployment-owned inventory snapshots."""

from __future__ import annotations

import copy
import re
from urllib.parse import urlsplit

from .discovery import approve, validate_observations, validate_scan_plan
from .inventory_io import (
    InventoryError, check_seal, decode, digest, path, publish, read_bytes,
    read_json, require_absent, seal, text,
)

MAX_DEVICES = 256
DECLARED_FIELDS = {"label", "manufacturer", "model", "device_type", "notes"}


def _identifier(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value) is None:
        raise InventoryError("invalid_inventory_selection")
    return value


def _source_url(value: object) -> str:
    value = text(value, limit=2048)
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or any(c.isspace() for c in value)):
            raise ValueError
    except ValueError:
        raise InventoryError("invalid_capability_catalog") from None
    return value


def lookup_capabilities(catalog: object, manufacturer: str | None,
                        model: str | None) -> list[dict]:
    """Exact identity lookup in an explicitly supplied, cited local catalog."""
    try:
        if (not isinstance(catalog, dict)
                or set(catalog) != {"schema_version", "devices"}
                or type(catalog["schema_version"]) is not int
                or catalog["schema_version"] != 1
                or not isinstance(catalog["devices"], list)
                or len(catalog["devices"]) > 1024):
            raise ValueError
        entries = {}
        for device in catalog["devices"]:
            if set(device) != {"manufacturer", "model", "capabilities"}:
                raise ValueError
            key = (text(device["manufacturer"]).strip().casefold(),
                   text(device["model"]).strip().casefold())
            if key in entries:
                raise ValueError
            capabilities = device["capabilities"]
            if not isinstance(capabilities, list) or len(capabilities) > 32:
                raise ValueError
            checked = []
            names = set()
            for capability in capabilities:
                if set(capability) != {"name", "source_url"}:
                    raise ValueError
                name = text(capability["name"])
                if name.casefold() in names:
                    raise ValueError
                names.add(name.casefold())
                checked.append({"name": name,
                                "source_url": _source_url(capability["source_url"]),
                                "evidence": "catalog-claim", "enabled": None})
            entries[key] = checked
        if manufacturer is None or model is None:
            return []
        return entries.get((manufacturer.strip().casefold(), model.strip().casefold()), [])
    except (KeyError, TypeError, ValueError, AttributeError):
        raise InventoryError("invalid_capability_catalog") from None


def validate_catalog(value: object) -> dict:
    catalog = check_seal(value, "inventory-catalog")
    try:
        if (set(catalog) != {"schema_version", "kind", "id", "devices"}
                or not isinstance(catalog["devices"], list)
                or len(catalog["devices"]) > MAX_DEVICES):
            raise ValueError
        ids = set()
        for device in catalog["devices"]:
            if set(device) != {"device_id", "declared", "observation",
                               "documented_capabilities"}:
                raise ValueError
            identity = _identifier(device["device_id"])
            if identity in ids:
                raise ValueError
            ids.add(identity)
            if set(device["declared"]) != DECLARED_FIELDS:
                raise ValueError
            for key, val in device["declared"].items():
                if val is not None:
                    text(val, limit=1024 if key == "notes" else 160, empty=True)
            validate_observations(device["observation"])
            if len(device["observation"]["hosts"]) != 1:
                raise ValueError
            capabilities = device["documented_capabilities"]
            if not isinstance(capabilities, list) or len(capabilities) > 32:
                raise ValueError
            for cap in capabilities:
                if (set(cap) != {"name", "source_url", "evidence", "enabled"}
                        or cap["evidence"] != "catalog-claim"
                        or cap["enabled"] is not None):
                    raise ValueError
                text(cap["name"])
                _source_url(cap["source_url"])
    except (KeyError, TypeError, ValueError, AttributeError):
        raise InventoryError("invalid_inventory_catalog") from None
    return catalog


def _input(value: str) -> tuple[object, dict]:
    source = path(value)
    content = read_bytes(source)
    return decode(content), {"path": str(source), "sha256": digest(content)}


def build_catalog_plan(observations_file: str, selection_file: str,
                       output: str, *, catalog_file: str | None = None,
                       previous_file: str | None = None) -> dict:
    output = str(path(output, output=True))
    raw, obs_input = _input(observations_file)
    observations = validate_observations(raw)
    selection, selection_input = _input(selection_file)
    inputs = {"observations": obs_input, "selection": selection_input,
              "capabilities": None, "previous": None}
    capabilities = None
    if catalog_file is not None:
        capabilities, inputs["capabilities"] = _input(catalog_file)
        lookup_capabilities(capabilities, None, None)
    devices = {}
    if previous_file is not None:
        previous, inputs["previous"] = _input(previous_file)
        devices = {d["device_id"]: copy.deepcopy(d)
                   for d in validate_catalog(previous)["devices"]}
    if any(i is not None and i["path"] == output for i in inputs.values()):
        raise InventoryError("inventory_target_exists")
    try:
        if (not isinstance(selection, dict)
                or set(selection) != {"schema_version", "devices"}
                or type(selection["schema_version"]) is not int
                or selection["schema_version"] != 1
                or not isinstance(selection["devices"], list)
                or not 1 <= len(selection["devices"]) <= MAX_DEVICES):
            raise ValueError
        hosts = {h["address"]: h for h in observations["hosts"]}
        selected_ids = set()
        selected_addresses = set()
        for item in selection["devices"]:
            if (not isinstance(item, dict)
                    or not {"device_id", "address"} <= set(item)
                    or not set(item) <= DECLARED_FIELDS | {"device_id", "address"}):
                raise ValueError
            identity = _identifier(item["device_id"])
            ip = text(item["address"])
            if ip not in hosts or identity in selected_ids or ip in selected_addresses:
                raise ValueError
            selected_ids.add(identity)
            selected_addresses.add(ip)
            previous = devices.get(identity)
            declared = ({k: None for k in DECLARED_FIELDS} if previous is None
                        else copy.deepcopy(previous["declared"]))
            for key in DECLARED_FIELDS & set(item):
                declared[key] = (None if item[key] is None else text(
                    item[key], limit=1024 if key == "notes" else 160, empty=True))
            old_caps = [] if previous is None else previous["documented_capabilities"]
            identity_changed = previous is not None and any(
                previous["declared"][k] != declared[k] for k in ("manufacturer", "model"))
            if identity_changed:
                old_caps = []
            matched = (old_caps if capabilities is None else lookup_capabilities(
                capabilities, declared["manufacturer"], declared["model"]))
            single = {k: copy.deepcopy(v) for k, v in observations.items()
                      if k not in {"id", "schema_version", "kind", "hosts"}}
            device_observation = seal("observations", **single, hosts=[hosts[ip]])
            devices[identity] = {
                "device_id": identity, "declared": declared,
                "observation": device_observation,
                "documented_capabilities": matched,
            }
        if len(devices) > MAX_DEVICES:
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError):
        raise InventoryError("invalid_inventory_selection") from None
    candidate = seal("inventory-catalog", devices=[devices[k] for k in sorted(devices)])
    validate_catalog(candidate)
    return seal("catalog-plan", inputs=inputs, output=output, catalog=candidate)


def validate_catalog_plan(value: object, *, recheck_inputs: bool = True) -> dict:
    plan = check_seal(value, "catalog-plan")
    try:
        if set(plan) != {"schema_version", "kind", "id", "inputs", "output", "catalog"}:
            raise ValueError
        inputs = plan["inputs"]
        if set(inputs) != {"observations", "selection", "capabilities", "previous"}:
            raise ValueError
        for key, source in inputs.items():
            if source is None and key in {"capabilities", "previous"}:
                continue
            if set(source) != {"path", "sha256"}:
                raise ValueError
            path(source["path"])
            if re.fullmatch(r"[a-f0-9]{64}", source["sha256"]) is None:
                raise ValueError
            if recheck_inputs and digest(read_bytes(source["path"])) != source["sha256"]:
                raise InventoryError("inventory_plan_stale")
        path(plan["output"], output=True)
        validate_catalog(plan["catalog"])
        if recheck_inputs:
            expected = build_catalog_plan(
                inputs["observations"]["path"], inputs["selection"]["path"], plan["output"],
                catalog_file=None if inputs["capabilities"] is None else inputs["capabilities"]["path"],
                previous_file=None if inputs["previous"] is None else inputs["previous"]["path"],
            )
            if expected != plan:
                raise InventoryError("inventory_plan_stale")
    except (KeyError, TypeError, ValueError, AttributeError):
        raise InventoryError("invalid_inventory_plan") from None
    return plan


def apply_catalog(plan: dict, approval: str) -> dict:
    # Approval is checked before reading any of the plan's referenced inputs.
    check_seal(plan, "catalog-plan")
    approve(plan, approval)
    validate_catalog_plan(plan)
    require_absent(plan["output"])
    publish(plan["output"], plan["catalog"])
    verify(plan)
    return plan["catalog"]


def verify(plan: dict) -> None:
    if isinstance(plan, dict) and plan.get("kind") == "scan-plan":
        validate_scan_plan(plan)
        observations = validate_observations(read_json(plan["output"]))
        if any(observations[key] != plan[key] for key in ("network", "mode", "targets")):
            raise InventoryError("inventory_verification_failed")
        if observations["plan_id"] != plan["id"]:
            raise InventoryError("inventory_verification_failed")
    else:
        validate_catalog_plan(plan, recheck_inputs=False)
        if read_json(plan["output"]) != plan["catalog"]:
            raise InventoryError("inventory_verification_failed")
