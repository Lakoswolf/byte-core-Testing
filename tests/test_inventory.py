from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byte_core import cli, discovery, inventory, inventory_io  # noqa: E402
from byte_core.inventory_io import InventoryError, encode, read_json, seal  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "inventory"


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.output = self.root / "observations.json"
        self.plan = discovery.build_scan_plan("192.0.2.0/24", str(self.output))

    def write(self, name, value):
        target = self.root / name
        target.write_bytes(encode(value))
        return str(target)

    def observe(self, *, inspect=False):
        if inspect:
            self.plan = discovery.build_scan_plan(
                "192.0.2.0/24", str(self.output), mode="inspect", targets=["192.0.2.10"])
        fixture = "inspect.xml.txt" if inspect else "discover.xml.txt"
        with patch.object(discovery, "_run_nmap", side_effect=AssertionError("network forbidden")):
            return discovery.scan(self.plan, self.plan["id"], xml_file=str(FIXTURES / fixture))

    def catalog_plan(self, **kwargs):
        return inventory.build_catalog_plan(
            str(self.output), str(FIXTURES / "selection.json"),
            str(self.root / "inventory.json"),
            catalog_file=str(FIXTURES / "capabilities.json"), **kwargs)

    def test_planning_is_deterministic_read_only_and_bounded(self):
        before = list(self.root.iterdir())
        with patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")):
            other = discovery.build_scan_plan("192.0.2.0/24", str(self.output))
        self.assertEqual(other, self.plan)
        self.assertEqual(before, list(self.root.iterdir()))
        self.assertIn("-sn", other["argv"])
        self.assertIn("--unprivileged", other["argv"])
        self.assertIn("-n", other["argv"])
        self.assertNotIn("-sV", other["argv"])
        self.assertNotIn("-A", other["argv"])

    def test_scope_refusals(self):
        cases = ["192.0.2.1/24", "192.0.2.0/23", "2001:db8::/64",
                 "scan.example.test", "--script=default", "0/0", "192.0.2.10"]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(InventoryError):
                discovery.build_scan_plan(value, str(self.output))

    def test_inspection_requires_explicit_in_scope_targets(self):
        for targets in ([], ["198.51.100.10"], ["192.0.2.10"] * 2,
                        [f"192.0.2.{n}" for n in range(1, 18)]):
            with self.subTest(targets=targets), self.assertRaises(InventoryError):
                discovery.build_scan_plan("192.0.2.0/24", str(self.output),
                                          mode="inspect", targets=targets)
        with self.assertRaises(InventoryError):
            discovery.build_scan_plan("192.0.2.0/24", str(self.output), targets=["192.0.2.10"])

    def test_wrong_approval_and_tampered_plan_never_start_scanner(self):
        changed = copy.deepcopy(self.plan)
        changed["argv"].append("-A")
        recalculated = seal("scan-plan", **{k: v for k, v in changed.items()
                                          if k not in {"kind", "schema_version", "id"}})
        with patch.object(discovery, "_run_nmap") as runner:
            for plan, approval in ((self.plan, "wrong"), (changed, changed["id"]),
                                   (recalculated, recalculated["id"])):
                with self.assertRaises(InventoryError):
                    discovery.scan(plan, approval)
            runner.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_import_is_private_scoped_and_does_not_confirm_identity(self):
        result = self.observe()
        self.assertEqual(result["source"], "imported-nmap-xml")
        self.assertEqual(len(result["hosts"]), 2)
        self.assertEqual(result["hosts"][0]["services"], [])
        self.assertNotIn("model", result["hosts"][0])
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        inventory.verify(self.plan)

    def test_inspection_keeps_service_type_as_hint(self):
        result = self.observe(inspect=True)
        hints = result["hosts"][0]["services"][0]["hints"]
        self.assertEqual(hints["devicetype"], "printer")
        self.assertNotIn("device_type", result["hosts"][0])

    def test_inspection_without_response_does_not_claim_reachability(self):
        plan = discovery.build_scan_plan("192.0.2.0/24", str(self.output),
                                         mode="inspect", targets=["192.0.2.10"])
        data = (FIXTURES / "discover.xml.txt").read_bytes()
        # Reuse just one fictional host for an explicitly targeted -Pn result.
        data = data.replace(b'<host><status state="up" reason="syn-ack"/>\n    <address addr="192.0.2.20" addrtype="ipv4"/>\n  </host>', b'')
        hosts = discovery.parse_nmap(data, plan)
        self.assertEqual(hosts[0]["reachability"], "unconfirmed")

    def test_invalid_xml_never_creates_observations(self):
        good = (FIXTURES / "discover.xml.txt").read_bytes()
        cases = [b"not xml", good.replace(b'exit="success"', b'exit="error"'),
                 good.replace(b"192.0.2.10", b"198.51.100.10"),
                 good.replace(b"192.0.2.20", b"192.0.2.10"),
                 good.replace(b"<!DOCTYPE nmaprun>", b'<!DOCTYPE nmaprun [<!ENTITY x "bad">]>'),
                 b"x" * (inventory_io.MAX_BYTES + 1)]
        with patch.object(discovery, "_run_nmap") as runner:
            for data in cases:
                runner.return_value = data
                with self.subTest(data=data[:40]), self.assertRaises(InventoryError):
                    discovery.scan(self.plan, self.plan["id"])
                self.assertFalse(self.output.exists())

    def test_unapproved_service_data_and_control_characters_are_rejected(self):
        data = (FIXTURES / "inspect.xml.txt").read_bytes()
        with self.assertRaises(InventoryError):
            discovery.parse_nmap(data, self.plan)
        plan = discovery.build_scan_plan("192.0.2.0/24", str(self.output),
                                         mode="inspect", targets=["192.0.2.10"])
        for bad in (data.replace(b'portid="631"', b'portid="9100"'),
                    data.replace(b'product="Fictional print service"', b'product="bad&#10;line"')):
            with self.assertRaises(InventoryError):
                discovery.parse_nmap(bad, plan)

    def test_existing_output_refuses_before_network_or_import(self):
        self.output.write_text("keep me")
        with patch.object(discovery, "_run_nmap") as runner:
            with self.assertRaisesRegex(InventoryError, "inventory_target_exists"):
                discovery.scan(self.plan, self.plan["id"])
            runner.assert_not_called()
        self.assertEqual(self.output.read_text(), "keep me")

    def test_output_in_core_or_git_metadata_is_refused(self):
        (self.root / ".git").mkdir()
        for target in (ROOT / "inventory.json", self.root / ".git" / "private.json"):
            with self.assertRaisesRegex(InventoryError, "inventory_output_in_repository"):
                discovery.build_scan_plan("192.0.2.0/24", str(target))

    def test_symlink_ancestor_input_and_output_are_refused(self):
        directory = self.root / "real"
        directory.mkdir()
        linked = self.root / "linked"
        linked.symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(InventoryError, "inventory_path_invalid"):
            discovery.build_scan_plan("192.0.2.0/24", str(linked / "output.json"))
        source = self.root / "source.json"
        source.symlink_to(FIXTURES / "selection.json")
        with self.assertRaisesRegex(InventoryError, "inventory_path_invalid"):
            read_json(source)

    def test_fifo_input_is_refused_without_blocking(self):
        source = self.root / "fifo"
        os.mkfifo(source)
        with self.assertRaisesRegex(InventoryError, "inventory_input_limit"):
            read_json(source)

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        for data in (b'{"devices": [], "devices": []}', b'{"value": NaN}'):
            with self.assertRaises(InventoryError):
                inventory_io.decode(data)

    def test_catalog_is_reviewed_selected_and_cited_without_claiming_enabled(self):
        self.observe(inspect=True)
        plan = self.catalog_plan()
        result = inventory.apply_catalog(plan, plan["id"])
        self.assertEqual(len(result["devices"]), 1)
        device = result["devices"][0]
        self.assertEqual(device["declared"]["model"], "Sample Printer 1")
        cap = device["documented_capabilities"][0]
        self.assertEqual(cap["evidence"], "catalog-claim")
        self.assertIsNone(cap["enabled"])
        self.assertEqual(cap["source_url"], "https://devices.example.test/sample-printer-1")
        inventory.verify(plan)

    def test_unknown_model_has_no_invented_capabilities(self):
        catalog = read_json(FIXTURES / "capabilities.json")
        for model in (None, "Sample Printer 2", "Sample"):
            self.assertEqual(inventory.lookup_capabilities(catalog, "Example Devices", model), [])

    def test_capability_catalog_refuses_ambiguous_matches_and_credential_urls(self):
        catalog = read_json(FIXTURES / "capabilities.json")
        duplicate = copy.deepcopy(catalog)
        duplicate["devices"].append(copy.deepcopy(duplicate["devices"][0]))
        invalid_url = copy.deepcopy(catalog)
        invalid_url["devices"][0]["capabilities"][0]["source_url"] = (
            "https://" + "reader@" + "devices.example.test/spec")
        for value in (duplicate, invalid_url):
            with self.assertRaises(InventoryError):
                inventory.lookup_capabilities(value, None, None)

    def test_changed_input_or_candidate_refuses_before_catalog_write(self):
        self.observe()
        local_selection = self.write("selection.json", read_json(FIXTURES / "selection.json"))
        plan = inventory.build_catalog_plan(str(self.output), local_selection,
                                            str(self.root / "inventory.json"))
        Path(local_selection).write_text("{}")
        with self.assertRaisesRegex(InventoryError, "inventory_plan_stale"):
            inventory.apply_catalog(plan, plan["id"])
        self.assertFalse((self.root / "inventory.json").exists())
        plan = self.catalog_plan()
        changed = copy.deepcopy(plan)
        changed["catalog"]["devices"][0]["declared"]["label"] = "changed"
        with self.assertRaises(InventoryError):
            inventory.apply_catalog(changed, changed["id"])

    def test_catalog_rejects_unseen_address_and_duplicate_selection(self):
        self.observe()
        base = read_json(FIXTURES / "selection.json")
        bad = copy.deepcopy(base)
        bad["devices"][0]["address"] = "192.0.2.30"
        duplicate = copy.deepcopy(base)
        duplicate["devices"].append(copy.deepcopy(duplicate["devices"][0]))
        for value in (bad, duplicate):
            selected = self.write("bad-selection.json", value)
            with self.assertRaises(InventoryError):
                inventory.build_catalog_plan(str(self.output), selected,
                                              str(self.root / "inventory.json"))

    def test_rescan_preserves_declared_corrections_and_unselected_devices(self):
        self.observe()
        initial = read_json(FIXTURES / "selection.json")
        initial["devices"].append({"device_id": "example-other", "address": "192.0.2.20",
                                   "label": "Keep this name"})
        selected = self.write("selection.json", initial)
        first_plan = inventory.build_catalog_plan(str(self.output), selected,
                                                  str(self.root / "first.json"))
        first = inventory.apply_catalog(first_plan, first_plan["id"])
        review = self.write("rescan-selection.json", {"schema_version": 1, "devices": [
            {"device_id": "example-printer", "address": "192.0.2.10"}]})
        next_plan = inventory.build_catalog_plan(str(self.output), review,
                                                 str(self.root / "next.json"),
                                                 previous_file=str(self.root / "first.json"))
        updated = inventory.apply_catalog(next_plan, next_plan["id"])
        self.assertEqual(first["devices"], updated["devices"])
        self.assertEqual(read_json(self.root / "first.json"), first)

    def test_new_model_clears_old_model_capabilities(self):
        self.observe()
        first_plan = self.catalog_plan()
        inventory.apply_catalog(first_plan, first_plan["id"])
        selection = self.write("new-model.json", {"schema_version": 1, "devices": [
            {"device_id": "example-printer", "address": "192.0.2.10", "model": "Unknown replacement"}]})
        plan = inventory.build_catalog_plan(str(self.output), selection,
                                            str(self.root / "new.json"),
                                            previous_file=str(self.root / "inventory.json"))
        self.assertEqual(plan["catalog"]["devices"][0]["documented_capabilities"], [])

    def test_wrong_catalog_approval_does_not_read_referenced_inputs(self):
        self.observe()
        plan = self.catalog_plan()
        with patch.object(inventory, "read_bytes") as reader:
            with self.assertRaisesRegex(InventoryError, "inventory_not_approved"):
                inventory.apply_catalog(plan, "wrong")
            reader.assert_not_called()

    def test_atomic_publication_preserves_a_racing_target(self):
        real_link = os.link
        def race(*args, **kwargs):
            self.output.write_text("other writer")
            return real_link(*args, **kwargs)
        with patch.object(inventory_io.os, "link", side_effect=race):
            with self.assertRaisesRegex(InventoryError, "inventory_target_exists"):
                inventory_io.publish(self.output, {"value": "ours"})
        self.assertEqual(self.output.read_text(), "other writer")
        self.assertEqual(list(self.root.glob(".byte-inventory-*")), [])

    def test_write_failure_publishes_nothing_and_cleans_temporary(self):
        with patch.object(inventory_io.os, "fsync", side_effect=OSError):
            with self.assertRaisesRegex(InventoryError, "inventory_write_failed"):
                inventory_io.publish(self.output, {"value": "fictional"})
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_runner_handles_missing_failure_timeout_and_output_limit(self):
        with patch.object(discovery.shutil, "which", return_value=None):
            with self.assertRaisesRegex(InventoryError, "nmap_unavailable"):
                discovery._run_nmap(["nmap"], 1)
        # Execute only tiny Python children; none can access the network.
        with patch.object(discovery.shutil, "which", return_value=sys.executable):
            cases = [("import sys; sys.exit(2)", 2, "inventory_scan_failed"),
                     ("import time; time.sleep(5)", 0.05, "inventory_scan_timeout"),
                     (f"print('x' * {inventory_io.MAX_BYTES + 1})", 2, "inventory_scan_output_limit")]
            for script, timeout, code in cases:
                with self.subTest(code=code), self.assertRaisesRegex(InventoryError, code):
                    discovery._run_nmap(["nmap", "-c", script], timeout)
            self.assertEqual(discovery._run_nmap(["nmap", "-c", "print('ok')"], 2), b"ok\n")

    def test_cli_offline_roundtrip_and_sanitized_failures(self):
        saved = self.write("scan-plan.json", self.plan)
        output, errors = io.StringIO(), io.StringIO()
        args = ["inventory", "import", "--plan", saved, "--approve", self.plan["id"],
                "--xml", str(FIXTURES / "discover.xml.txt")]
        with patch.object(discovery, "_run_nmap", side_effect=AssertionError("network forbidden")):
            self.assertEqual(cli.main(args, stdout=output, stderr=errors), 0)
        self.assertIn("Result: observations_saved", output.getvalue())
        self.assertIn("Source: imported-nmap-xml", output.getvalue())
        self.assertEqual(errors.getvalue(), "")
        output, errors = io.StringIO(), io.StringIO()
        self.assertEqual(cli.main(args, stdout=output, stderr=errors), 5)
        self.assertEqual(errors.getvalue(), "byte: inventory_target_exists\n")
        self.assertNotIn(str(self.root), errors.getvalue())

    def test_live_cli_refuses_unsupported_host_before_scanner(self):
        saved = self.write("scan-plan.json", self.plan)
        class Unsupported:
            supported = False
        with patch.object(cli, "collect_check_report", return_value=Unsupported()), \
                patch.object(discovery, "_run_nmap") as runner:
            code = cli.main(["inventory", "scan", "--plan", saved,
                             "--approve", self.plan["id"]], stderr=io.StringIO())
        self.assertEqual(code, 3)
        runner.assert_not_called()

    def test_live_adapter_runs_only_exact_arguments_and_marks_live_source(self):
        xml = (FIXTURES / "discover.xml.txt").read_bytes()
        with patch.object(discovery, "_run_nmap", return_value=xml) as runner:
            result = discovery.scan(self.plan, self.plan["id"])
        runner.assert_called_once_with(self.plan["argv"], self.plan["timeout_seconds"])
        self.assertEqual(result["source"], "nmap")
        self.assertNotIn("192.0.2.0", self.plan["argv"])
        self.assertNotIn("192.0.2.255", self.plan["argv"])

    def test_cli_complete_offline_workflow(self):
        def invoke(*args):
            output, errors = io.StringIO(), io.StringIO()
            code = cli.main(["inventory", *args], stdout=output, stderr=errors)
            self.assertEqual(code, 0, errors.getvalue())
            return json.loads(output.getvalue())
        with patch.object(discovery, "_run_nmap", side_effect=AssertionError("network forbidden")):
            plan = invoke("plan", "--network", "192.0.2.0/24", "--output", str(self.output))
            plan_file = self.write("plan.json", plan)
            result = invoke("import", "--plan", plan_file, "--approve", plan["id"],
                            "--xml", str(FIXTURES / "discover.xml.txt"), "--format", "json")
            self.assertEqual(result["devices"], 2)
            lookup = invoke("lookup", "--capabilities", str(FIXTURES / "capabilities.json"),
                            "--manufacturer", "Example Devices", "--model", "Sample Printer 1")
            self.assertEqual(len(lookup["capabilities"]), 1)
            catalog = invoke("plan-catalog", "--observations", str(self.output),
                             "--selection", str(FIXTURES / "selection.json"),
                             "--capabilities", str(FIXTURES / "capabilities.json"),
                             "--output", str(self.root / "catalog.json"))
            catalog_file = self.write("catalog-plan.json", catalog)
            applied = invoke("apply", "--plan", catalog_file, "--approve", catalog["id"],
                             "--format", "json")
            self.assertEqual(applied["code"], "inventory_saved")
            checked = invoke("verify", "--plan", catalog_file, "--format", "json")
            self.assertEqual(checked["code"], "verified")

    def test_canonical_documents_are_preserved_when_catalog_is_added(self):
        from byte_core.lifecycle import build_initialization_plan, apply_initialization
        deployment = self.root / "deployment"
        apply_initialization(build_initialization_plan(deployment))
        original = {p.name: p.read_bytes() for p in deployment.iterdir()}
        self.observe()
        plan = inventory.build_catalog_plan(str(self.output), str(FIXTURES / "selection.json"),
                                             str(deployment / "inventory.json"))
        inventory.apply_catalog(plan, plan["id"])
        self.assertEqual({name: (deployment / name).read_bytes() for name in original}, original)

    def test_ancestor_link_swap_cannot_redirect_publication(self):
        parent = self.root / "parent"
        parent.mkdir()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        original_open = inventory_io._open_parent
        def redirect(target):
            parent.rmdir()
            parent.symlink_to(elsewhere, target_is_directory=True)
            return original_open(target)
        with patch.object(inventory_io, "_open_parent", side_effect=redirect):
            with self.assertRaisesRegex(InventoryError, "inventory_write_failed"):
                inventory_io.publish(parent / "result.json", {"data": "fictional"})
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_resealed_candidate_tampering_is_rederived_and_refused(self):
        self.observe()
        plan = self.catalog_plan()
        candidate = copy.deepcopy(plan["catalog"])
        candidate["devices"][0]["declared"]["label"] = "Unreviewed label"
        candidate = seal("inventory-catalog", devices=candidate["devices"])
        altered = seal("catalog-plan", inputs=plan["inputs"], output=plan["output"], catalog=candidate)
        with self.assertRaisesRegex(InventoryError, "inventory_plan_stale"):
            inventory.apply_catalog(altered, altered["id"])
        self.assertFalse((self.root / "inventory.json").exists())


if __name__ == "__main__":
    unittest.main()
