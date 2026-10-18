"""Offline, exact-scope plans for optional reachability and wake requests."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import ipaddress
import json
import math
import re
import shlex
import shutil
import socket
import subprocess
import sys


class NetworkHelperError(ValueError):
    """An invalid setting, changed plan, or missing approval."""


def _fail(message: str) -> None:
    raise NetworkHelperError(message)


def _text(value: object, field: str, maximum: int = 256) -> str:
    if (type(value) is not str or not value or len(value) > maximum
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        _fail(f"configure a valid {field}")
    return value


def _settings(config: dict) -> dict:
    values = config.get("network", {})
    if type(values) is not dict or set(values) - {"ping_timeout", "workers", "relay_timeout"}:
        _fail("invalid network settings")
    result = {"ping_timeout": 2, "workers": 4, "relay_timeout": 10, **values}
    for key, maximum in (("ping_timeout", 10), ("relay_timeout", 30)):
        value = result[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= maximum:
            _fail(f"configure {key} greater than zero and at most {maximum}")
    if type(result["workers"]) is not int or not 1 <= result["workers"] <= 8:
        _fail("configure workers as an integer from 1 to 8")
    return result


def _relay_host(value: object) -> str:
    host = _text(value, "relay_host")
    parts = host.split("@")
    if len(parts) > 2 or (len(parts) == 2 and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", parts[0])):
        _fail("configure relay_host as a host or user@host")
    destination = parts[-1]
    if destination.startswith("[") and destination.endswith("]"):
        try:
            ipaddress.IPv6Address(destination[1:-1])
        except ValueError:
            _fail("configure a valid relay_host")
        if "%" in destination:
            _fail("relay_host scope identifiers are unsupported")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", destination):
        _fail("configure a valid relay_host")
    return host


def _devices(config: dict) -> dict:
    if type(config) is not dict:
        _fail("invalid helper configuration")
    devices = config.get("devices", [])
    if type(devices) is not list or len(devices) > 64:
        _fail("configure at most 64 devices")
    result = {}
    allowed = {"name", "addresses", "mac", "broadcast", "port", "relay_host", "relay_command"}
    for device in devices:
        if type(device) is not dict or set(device) - allowed:
            _fail("invalid device settings")
        name = _text(device.get("name"), "device name", 80)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name in result:
            _fail("device names must be unique and contain only letters, digits, dots, underscores, or hyphens")
        addresses = device.get("addresses", [])
        if type(addresses) is not list or len(addresses) > 8:
            _fail("configure at most 8 numeric addresses per device")
        normalized = []
        for address in addresses:
            address = _text(address, "numeric device address")
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError:
                _fail("configure numeric device addresses; DNS names are unsupported")
            if "%" in address:
                _fail("address scope identifiers are unsupported")
            canonical = str(parsed)
            if canonical in normalized:
                _fail("device addresses must be unique")
            normalized.append(canonical)
        value = {**device, "name": name, "addresses": normalized}
        if "mac" in value:
            mac = _text(value["mac"], "MAC address")
            if not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", mac):
                _fail("configure MAC as six colon-separated hexadecimal octets")
            octets = bytes.fromhex(mac.replace(":", ""))
            if octets == bytes(6) or octets[0] & 1:
                _fail("configure a nonzero unicast MAC address")
            value["mac"] = mac.lower()
        if "broadcast" in value:
            try:
                value["broadcast"] = str(ipaddress.IPv4Address(_text(value["broadcast"], "broadcast IPv4 address")))
            except ValueError:
                _fail("configure a numeric broadcast IPv4 address")
        if "port" in value and (type(value["port"]) is not int or not 1 <= value["port"] <= 65535):
            _fail("configure port as an integer from 1 to 65535")
        if "relay_host" in value:
            value["relay_host"] = _relay_host(value["relay_host"])
        if "relay_command" in value:
            command = value["relay_command"]
            if type(command) is not list or not 1 <= len(command) <= 32:
                _fail("configure relay_command as 1 to 32 arguments")
            for argument in command:
                _text(argument, "relay_command argument", 1024)
            if not command[0].startswith("/") or ".." in command[0].split("/"):
                _fail("configure relay executable as an absolute path without parent traversal")
            value["relay_command"] = command.copy()
        if ("relay_host" in value) != ("relay_command" in value):
            _fail("configure both relay_host and relay_command")
        result[name] = value
    return result


def validate_settings(config: dict) -> dict:
    """Validate and normalize network settings without I/O or changing input data."""
    return {"devices": list(_devices(config).values()), "network": _settings(config)}


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _plan(kind: str, **fields: object) -> dict:
    value = {"schema_version": 1, "kind": kind, **fields}
    return {**value, "id": hashlib.sha256(_canonical(value).encode()).hexdigest()}


def plan_status(config: dict, device_names: list[str]) -> dict:
    """Select named devices without resolving programs, contacting hosts, or writing."""
    devices = _devices(config)
    settings = _settings(config)
    if (type(device_names) is not list or not 1 <= len(device_names) <= 64
            or any(type(name) is not str for name in device_names)
            or len(set(device_names)) != len(device_names)):
        _fail("select 1 to 64 unique configured device names")
    if any(name not in devices for name in device_names):
        _fail("unknown device; configure the selected device before planning")
    return _plan("labstatus_plan", device_names=device_names.copy(),
                 devices=[devices[name] for name in device_names], settings=settings,
                 operation="one ICMP echo per numeric address", backout="sent probes cannot be recalled")


def plan_wake(config: dict, device_name: str) -> dict:
    """Describe one exact direct packet or one configured SSH sender invocation."""
    devices = _devices(config)
    settings = _settings(config)
    if type(device_name) is not str or device_name not in devices:
        _fail("unknown device; configure the selected device before planning")
    device = devices[device_name]
    if "mac" not in device:
        _fail("configure the selected device MAC before requesting wake")
    delivery = "ssh" if "relay_host" in device else "udp"
    if delivery == "udp" and not {"broadcast", "port"} <= set(device):
        _fail("configure explicit broadcast and port for direct wake delivery")
    return _plan("wakelan_plan", device_name=device_name, device=device,
                 delivery=delivery, settings=settings,
                 operation="request wake; power state is not verified",
                 backout="sent wake requests cannot be recalled")


def _approved(config: dict, plan: dict, approval: str, kind: str) -> dict:
    if type(plan) is not dict or plan.get("kind") != kind:
        _fail("invalid network plan")
    if kind == "labstatus_plan":
        expected = plan_status(config, plan.get("device_names"))
    else:
        expected = plan_wake(config, plan.get("device_name"))
    try:
        matches = _canonical(plan) == _canonical(expected)
    except (TypeError, ValueError):
        matches = False
    if not matches:
        _fail("network plan changed or configuration is stale; create and review a new plan")
    if type(approval) is not str or approval != expected["id"]:
        _fail("network operation requires approval of the exact plan ID")
    return expected


def _ping(address: str, timeout: float) -> dict:
    version = ipaddress.ip_address(address).version
    if sys.platform not in ("linux", "darwin"):
        return {"address": address, "status": "unavailable"}
    name = "ping6" if sys.platform == "darwin" and version == 6 else "ping"
    executable = shutil.which(name)
    if executable is None:
        return {"address": address, "status": "unavailable"}
    argv = [executable, "-n", "-c", "1"]
    if sys.platform == "linux":
        argv.append("-6" if version == 6 else "-4")
    argv.append(address)
    try:
        process = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        # BSD ping uses 2 for no replies; Linux uses 1.
        no_reply = 2 if sys.platform == "darwin" else 1
        status = "reachable" if process.returncode == 0 else "no_response" if process.returncode == no_reply else "error"
    except subprocess.TimeoutExpired:
        status = "no_response"
    except FileNotFoundError:
        status = "unavailable"
    except OSError:
        status = "error"
    return {"address": address, "status": status}


def run_status(config: dict, plan: dict, approve: str) -> dict:
    """Run only the reviewed probes, returning observations without claiming offline state."""
    plan = _approved(config, plan, approve, "labstatus_plan")
    settings = plan["settings"]
    targets = [address for device in plan["devices"] for address in device["addresses"]]
    with ThreadPoolExecutor(max_workers=settings["workers"]) as executor:
        observations = iter(executor.map(lambda address: _ping(address, settings["ping_timeout"]), targets))
        results = []
        for device in plan["devices"]:
            addresses = [next(observations) for _ in device["addresses"]]
            states = {item["status"] for item in addresses}
            status = next((candidate for candidate in ("reachable", "error", "unavailable", "no_response")
                           if candidate in states), "no_addresses")
            results.append({"name": device["name"], "status": status, "addresses": addresses})
    return {"kind": "labstatus_result", "plan_id": plan["id"], "devices": results}


def run_wake(config: dict, plan: dict, approve: str) -> dict:
    """Send a single request; success never asserts that the target powered on."""
    plan = _approved(config, plan, approve, "wakelan_plan")
    device = plan["device"]
    status = "error"
    if plan["delivery"] == "udp":
        packet = b"\xff" * 6 + bytes.fromhex(device["mac"].replace(":", "")) * 16
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                sender.settimeout(plan["settings"]["relay_timeout"])
                sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sent = sender.sendto(packet, (device["broadcast"], device["port"]))
            status = "sent" if sent == len(packet) else "error"
        except OSError:
            status = "error"
    else:
        executable = shutil.which("ssh")
        if executable is None:
            status = "unavailable"
        else:
            # Ignore SSH config to prevent implicit relays, forwards, or local commands.
            argv = [executable, "-F", "/dev/null", "-T", "-oBatchMode=yes",
                    "-oStrictHostKeyChecking=yes", "-oClearAllForwardings=yes",
                    "-oPermitLocalCommand=no", "-oForwardAgent=no", "--",
                    device["relay_host"], shlex.join(device["relay_command"])]
            try:
                process = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL,
                                         timeout=plan["settings"]["relay_timeout"], check=False)
                status = "requested" if process.returncode == 0 else "error"
            except subprocess.TimeoutExpired:
                status = "unknown"
            except FileNotFoundError:
                status = "unavailable"
            except OSError:
                status = "error"
    return {"kind": "wakelan_result", "plan_id": plan["id"], "name": device["name"],
            "delivery": plan["delivery"], "status": status, "power_state": "unknown"}
