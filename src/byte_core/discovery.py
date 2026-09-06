"""Explicit, bounded Nmap discovery and separately approved service inspection."""

from __future__ import annotations

import ipaddress
import os
import re
import selectors
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .inventory_io import (
    MAX_BYTES, InventoryError, check_seal, path, publish, read_bytes,
    require_absent, seal, text,
)

MAX_HOSTS = 256
MAX_INSPECT_TARGETS = 16
INSPECT_PORTS = (22, 80, 443, 445, 515, 631, 3389, 8080, 8443)
SCAN_TIMEOUT = 180
# RFC 1918 prefix constants, followed by the RFC 5737 documentation ranges.
# These define protocol scope; they are not a deployment's discovered networks.
ALLOWED_NETWORKS = tuple(ipaddress.IPv4Network(n) for n in (
    (0x0A000000, 8), (0xAC100000, 12), (0xC0A80000, 16),
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",
))


def network(value: object) -> ipaddress.IPv4Network:
    try:
        if not isinstance(value, str) or "/" not in value:
            raise ValueError
        result = ipaddress.ip_network(value, strict=True)
        if (result.version != 4 or result.num_addresses > MAX_HOSTS
                or not any(result.subnet_of(n) for n in ALLOWED_NETWORKS)):
            raise ValueError
        return result
    except (ValueError, TypeError):
        raise InventoryError("inventory_network_invalid") from None


def address(value: object, subnet: ipaddress.IPv4Network) -> str:
    try:
        if not isinstance(value, str):
            raise ValueError
        item = ipaddress.IPv4Address(value)
        if item not in subnet:
            raise ValueError
        if subnet.prefixlen < 31 and item in (
                subnet.network_address, subnet.broadcast_address):
            raise ValueError
        return str(item)
    except (ValueError, TypeError):
        raise InventoryError("inventory_target_out_of_scope") from None


def build_scan_plan(subnet: str, output: str, *, mode: str = "discover",
                    targets: list[str] | None = None) -> dict:
    scope = network(subnet)
    if not isinstance(mode, str) or mode not in {"discover", "inspect"}:
        raise InventoryError("invalid_inventory_plan")
    if targets is None:
        targets = []
    if not isinstance(targets, list) or len(targets) > MAX_INSPECT_TARGETS:
        raise InventoryError("invalid_inventory_plan")
    selected = sorted({address(t, scope) for t in targets},
                      key=ipaddress.IPv4Address)
    if len(selected) != len(targets) or bool(selected) != (mode == "inspect"):
        raise InventoryError("invalid_inventory_plan")
    argv = ["nmap", "--unprivileged", "-n", "--disable-arp-ping",
            "--max-retries", "1", "--max-rate", "20",
            "--host-timeout", "15s", "-oX", "-"]
    if mode == "discover":
        argv += ["-sn", "-PS80,443", *(str(ip) for ip in scope.hosts())]
    else:
        argv += ["-sT", "-sV", "--version-light", "-Pn", "-p",
                 ",".join(map(str, INSPECT_PORTS)), *selected]
    return seal("scan-plan", network=str(scope), mode=mode,
                targets=selected, output=str(path(output, output=True)),
                argv=argv, timeout_seconds=SCAN_TIMEOUT)


def validate_scan_plan(value: object) -> dict:
    plan = check_seal(value, "scan-plan")
    try:
        expected = build_scan_plan(plan["network"], plan["output"],
                                   mode=plan["mode"], targets=plan["targets"])
    except (KeyError, TypeError):
        raise InventoryError("invalid_inventory_plan") from None
    if plan != expected:
        raise InventoryError("invalid_inventory_plan")
    return plan


def approve(plan: dict, approval: str) -> None:
    if approval != plan["id"]:
        raise InventoryError("inventory_not_approved")


def _run_nmap(argv: list[str], timeout: int) -> bytes:
    """Do not retain or echo stderr; cap stdout while the child is running."""
    executable = shutil.which("nmap")
    if executable is None:
        raise InventoryError("nmap_unavailable")
    process = None
    try:
        process = subprocess.Popen(
            [executable, *argv[1:]], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            shell=False, close_fds=True,
        )
        deadline = time.monotonic() + timeout
        chunks = []
        size = 0
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise InventoryError("inventory_scan_timeout")
                for key, _ in selector.select(min(remaining, 0.2)):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise InventoryError("inventory_scan_output_limit")
                    chunks.append(chunk)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InventoryError("inventory_scan_timeout")
            if process.wait(timeout=remaining) != 0:
                raise InventoryError("inventory_scan_failed")
        return b"".join(chunks)
    except subprocess.TimeoutExpired:
        raise InventoryError("inventory_scan_timeout") from None
    except OSError:
        raise InventoryError("inventory_scan_failed") from None
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            if process.stdout is not None:
                process.stdout.close()


def _hint(value: str | None) -> str | None:
    return None if value is None else text(value)


def parse_nmap(data: bytes, plan: dict) -> list[dict]:
    """Extract only scoped hosts and bounded identity/service hints."""
    validate_scan_plan(plan)
    if len(data) > MAX_BYTES:
        raise InventoryError("inventory_scan_output_limit")
    try:
        xml = data.decode("utf-8")
        # Nmap emits this harmless doctype. All other DTD/entity forms fail.
        xml = xml.replace("<!DOCTYPE nmaprun>", "")
        if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper() or "\0" in xml:
            raise ValueError
        root = ET.fromstring(xml)
        finished = root.find("runstats/finished")
        if (root.tag != "nmaprun" or root.get("scanner") != "nmap"
                or finished is None or finished.get("exit") != "success"):
            raise ValueError
        hosts = root.findall("host")
        if len(hosts) > MAX_HOSTS:
            raise ValueError
    except (UnicodeError, ValueError, ET.ParseError, RecursionError):
        raise InventoryError("invalid_discovery_xml") from None
    scope = network(plan["network"])
    result = []
    seen = set()
    for host in hosts:
        addresses = host.findall("address[@addrtype='ipv4']")
        if len(addresses) != 1:
            raise InventoryError("invalid_discovery_xml")
        ip = address(addresses[0].get("addr"), scope)
        if plan["mode"] == "inspect" and ip not in plan["targets"]:
            raise InventoryError("inventory_target_out_of_scope")
        if ip in seen:
            raise InventoryError("invalid_discovery_xml")
        seen.add(ip)
        status = host.find("status")
        if status is None or status.get("state") not in {"up", "down"}:
            raise InventoryError("invalid_discovery_xml")
        ports = host.findall("ports/port")
        if len(ports) > len(INSPECT_PORTS) or (ports and plan["mode"] != "inspect"):
            raise InventoryError("invalid_discovery_xml")
        services = []
        port_ids = set()
        for port in ports:
            try:
                number = int(port.get("portid", ""))
            except ValueError:
                raise InventoryError("invalid_discovery_xml") from None
            if (port.get("protocol") != "tcp" or number not in INSPECT_PORTS
                    or number in port_ids):
                raise InventoryError("invalid_discovery_xml")
            port_ids.add(number)
            state = port.find("state")
            if state is None or state.get("state") not in {
                    "open", "closed", "filtered", "unfiltered",
                    "open|filtered", "closed|filtered"}:
                raise InventoryError("invalid_discovery_xml")
            if state.get("state") != "open":
                continue
            service = port.find("service")
            services.append({
                "port": number, "transport": "tcp",
                "hints": {} if service is None else {
                    key: _hint(service.get(key)) for key in (
                        "name", "product", "version", "devicetype", "ostype"
                    ) if service.get(key) is not None
                },
            })
        if status.get("state") != "up":
            continue
        names = host.findall("hostnames/hostname")
        if len(names) > 8:
            raise InventoryError("invalid_discovery_xml")
        # MAC/vendor and hostnames are hints, never confirmed model identity.
        macs = host.findall("address[@addrtype='mac']")
        if len(macs) > 1:
            raise InventoryError("invalid_discovery_xml")
        result.append({
            "address": ip,
            "reachability": ("responded" if plan["mode"] == "discover" or services
                             else "unconfirmed"),
            "hostnames": sorted({text(n.get("name")) for n in names}),
            "mac_hint": _hint(macs[0].get("addr")) if macs else None,
            "vendor_hint": _hint(macs[0].get("vendor")) if macs else None,
            "services": sorted(services, key=lambda s: s["port"]),
        })
    return sorted(result, key=lambda h: ipaddress.IPv4Address(h["address"]))


def scan(plan: dict, approval: str, *, xml_file: str | None = None) -> dict:
    plan = validate_scan_plan(plan)
    approve(plan, approval)
    require_absent(plan["output"])
    data = (read_bytes(xml_file) if xml_file is not None
            else _run_nmap(plan["argv"], plan["timeout_seconds"]))
    hosts = parse_nmap(data, plan)
    observations = seal(
        "observations", plan_id=plan["id"], network=plan["network"],
        mode=plan["mode"], targets=plan["targets"],
        source="imported-nmap-xml" if xml_file is not None else "nmap",
        recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        hosts=hosts,
    )
    publish(plan["output"], observations)
    return observations


def validate_observations(value: object) -> dict:
    result = check_seal(value, "observations")
    try:
        if set(result) != {"schema_version", "kind", "id", "plan_id",
                           "network", "mode", "targets", "source",
                           "recorded_at", "hosts"}:
            raise ValueError
        scope = network(result["network"])
        if result["source"] not in {"nmap", "imported-nmap-xml"}:
            raise ValueError
        stamp = datetime.fromisoformat(result["recorded_at"])
        if stamp.utcoffset() is None:
            raise ValueError
        if (not isinstance(result["hosts"], list)
                or len(result["hosts"]) > MAX_HOSTS):
            raise ValueError
        seen = set()
        for host in result["hosts"]:
            if set(host) != {"address", "reachability", "hostnames", "mac_hint",
                             "vendor_hint", "services"}:
                raise ValueError
            ip = address(host["address"], scope)
            if ip in seen:
                raise ValueError
            seen.add(ip)
            if host["reachability"] not in {"responded", "unconfirmed"}:
                raise ValueError
            if not isinstance(host["hostnames"], list) or len(host["hostnames"]) > 8:
                raise ValueError
            for name in host["hostnames"]:
                text(name)
            for key in ("mac_hint", "vendor_hint"):
                if host[key] is not None:
                    text(host[key])
            if not isinstance(host["services"], list) or len(host["services"]) > len(INSPECT_PORTS):
                raise ValueError
            port_ids = set()
            for service in host["services"]:
                if (set(service) != {"port", "transport", "hints"}
                        or type(service["port"]) is not int
                        or service["port"] not in INSPECT_PORTS
                        or service["port"] in port_ids
                        or service["transport"] != "tcp"
                        or not isinstance(service["hints"], dict)
                        or not set(service["hints"]) <= {
                            "name", "product", "version", "devicetype", "ostype"}):
                    raise ValueError
                port_ids.add(service["port"])
                for hint in service["hints"].values():
                    text(hint)
        # Validate mode, scope and target shape using the same planner rules.
        if result["mode"] not in {"discover", "inspect"}:
            raise ValueError
        targets = result["targets"]
        if not isinstance(targets, list) or len(targets) > MAX_INSPECT_TARGETS:
            raise ValueError
        selected = {address(t, scope) for t in targets}
        if (len(selected) != len(targets)
                or bool(selected) != (result["mode"] == "inspect")
                or (selected and not seen <= selected)
                or (not selected and any(h["services"] for h in result["hosts"]))):
            raise ValueError
        if re.fullmatch(r"[a-f0-9]{64}", result["plan_id"]) is None:
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError):
        raise InventoryError("invalid_inventory_input") from None
    return result
