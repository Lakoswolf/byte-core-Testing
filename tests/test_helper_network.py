"""Fictional network inputs; every traffic-producing interface is mocked."""
from __future__ import annotations

import copy
import shlex
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from byte_core import helper_network as network


def configuration():
    return {"devices": [
        {"name": "fictional-lamp", "addresses": ["192.0.2.11", "2001:db8::11"],
         "mac": "02:00:00:00:00:11", "broadcast": "192.0.2.255", "port": 9},
        {"name": "fictional-empty", "addresses": []},
    ]}


class NetworkHelperTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.run = mock.patch.object(network.subprocess, "run").start()
        self.socket = mock.patch.object(network.socket, "socket").start()
        self.which = mock.patch.object(network.shutil, "which", return_value="/fictional/bin/ping").start()
        self.addCleanup(mock.patch.stopall)

    def assert_no_traffic(self):
        self.run.assert_not_called()
        self.socket.assert_not_called()

    def test_validation_normalizes_without_io_or_mutating_input(self):
        self.config["devices"][0].update(
            addresses=["2001:0db8:0000::0011"], mac="02:00:00:00:00:AB",
            relay_host="operator@[2001:db8::12]", relay_command=["/opt/fictional/sender", "--wake"])
        original = copy.deepcopy(self.config)
        normalized = network.validate_settings(self.config)
        self.assertEqual(normalized["devices"][0]["addresses"], ["2001:db8::11"])
        self.assertEqual(normalized["devices"][0]["mac"], "02:00:00:00:00:ab")
        self.assertEqual(normalized["network"], {"ping_timeout": 2, "workers": 4, "relay_timeout": 10})
        self.assertEqual(self.config, original)
        normalized["devices"][0]["relay_command"].append("--another")
        self.assertEqual(self.config, original)
        self.assert_no_traffic()
        self.which.assert_not_called()

    def test_validation_refuses_zero_mac_duplicate_addresses_and_invalid_relay(self):
        for update in (
            {"mac": "00:00:00:00:00:00"},
            {"addresses": ["2001:db8::11", "2001:0db8:0000::0011"]},
            {"relay_host": "relay.example", "relay_command": ["sender"]},
            {"relay_host": "relay.example", "relay_command": ["/opt/../sender"]},
            {"relay_host": "operator@@relay.example", "relay_command": ["/opt/sender"]},
            {"relay_host": "[not-ipv6]", "relay_command": ["/opt/sender"]},
        ):
            config = configuration()
            config["devices"][0].update(update)
            with self.subTest(update=update):
                with self.assertRaises(network.NetworkHelperError):
                    network.validate_settings(config)
        self.assert_no_traffic()
        self.which.assert_not_called()

    def test_plans_and_unapproved_requests_never_contact_targets(self):
        for make, apply, selection in (
            (network.plan_status, network.run_status, ["fictional-lamp", "fictional-empty"]),
            (network.plan_wake, network.run_wake, "fictional-lamp"),
        ):
            with self.subTest(operation=make.__name__):
                plan = make(self.config, selection)
                self.assertEqual(plan, make(self.config, selection))
                with self.assertRaisesRegex(network.NetworkHelperError, "exact plan ID"):
                    apply(self.config, plan, "")
                self.assert_no_traffic()
                self.which.assert_not_called()

    def test_edited_stale_and_cross_operation_plans_refuse_before_traffic(self):
        for make, apply, selection in (
            (network.plan_status, network.run_status, ["fictional-lamp"]),
            (network.plan_wake, network.run_wake, "fictional-lamp"),
        ):
            plan = make(self.config, selection)
            edited = copy.deepcopy(plan)
            edited["settings"]["workers"] = 8
            with self.assertRaisesRegex(network.NetworkHelperError, "stale"):
                apply(self.config, edited, plan["id"])
            edited = copy.deepcopy(plan)
            edited["schema_version"] = True
            with self.assertRaises(network.NetworkHelperError):
                apply(self.config, edited, plan["id"])
            stale = copy.deepcopy(self.config)
            stale["devices"][0]["addresses"] = ["192.0.2.12"]
            with self.assertRaisesRegex(network.NetworkHelperError, "stale"):
                apply(stale, plan, plan["id"])
        wake = network.plan_wake(self.config, "fictional-lamp")
        with self.assertRaises(network.NetworkHelperError):
            network.run_status(self.config, wake, wake["id"])
        self.assert_no_traffic()

    def test_invalid_settings_and_unknown_facts_refuse_without_traffic(self):
        mutations = [
            lambda config: config["devices"][0].update(addresses=["lamp.example"]),
            lambda config: config["devices"][0].update(addresses=["2001:db8::1%fictional0"]),
            lambda config: config["devices"][0].update(addresses=["192.0.2.1"] * 9),
            lambda config: config["devices"][0].update(mac="ff:ff:ff:ff:ff:ff"),
            lambda config: config["devices"][0].update(port=True),
            lambda config: config["devices"][0].update(broadcast="lamp.example"),
            lambda config: config.update(network={"workers": 9}),
            lambda config: config.update(network={"ping_timeout": float("nan")}),
            lambda config: config.update(network={"relay_timeout": 31}),
            lambda config: config.update(network={"ping_timeout": 0}),
            lambda config: config["devices"][0].update(relay_host="-oProxyCommand=bad"),
            lambda config: config["devices"][0].update(relay_host="host.example\ncommand"),
            lambda config: config["devices"][0].update(relay_command=["./sender"]),
        ]
        for mutate in mutations:
            config = configuration()
            mutate(config)
            with self.subTest(config=config):
                with self.assertRaises(network.NetworkHelperError):
                    network.plan_status(config, ["fictional-lamp"])
        with self.assertRaisesRegex(network.NetworkHelperError, "unknown device"):
            network.plan_status(self.config, ["missing"])
        with self.assertRaisesRegex(network.NetworkHelperError, "MAC"):
            network.plan_wake(self.config, "fictional-empty")
        del self.config["devices"][0]["port"]
        with self.assertRaisesRegex(network.NetworkHelperError, "broadcast and port"):
            network.plan_wake(self.config, "fictional-lamp")
        self.assert_no_traffic()
        self.which.assert_not_called()

    @mock.patch.object(network.sys, "platform", "linux")
    def test_status_uses_bounded_numeric_probes_and_preserves_unknown_facts(self):
        self.config["network"] = {"workers": 1, "ping_timeout": 0.5}
        plan = network.plan_status(self.config, ["fictional-lamp", "fictional-empty"])
        self.run.side_effect = [mock.Mock(returncode=1), mock.Mock(returncode=0)]
        result = network.run_status(self.config, plan, plan["id"])
        self.assertEqual(result["devices"][0]["status"], "reachable")
        self.assertEqual(result["devices"][1], {"name": "fictional-empty", "status": "no_addresses", "addresses": []})
        self.assertEqual([item["status"] for item in result["devices"][0]["addresses"]], ["no_response", "reachable"])
        calls = self.run.call_args_list
        self.assertEqual(calls[0].args[0], ["/fictional/bin/ping", "-n", "-c", "1", "-4", "192.0.2.11"])
        self.assertEqual(calls[1].args[0][-2:], ["-6", "2001:db8::11"])
        for call in calls:
            self.assertEqual(call.kwargs["timeout"], 0.5)
            self.assertEqual(call.kwargs["stdout"], subprocess.DEVNULL)
            self.assertNotIn("shell", call.kwargs)
        self.socket.assert_not_called()

    @mock.patch.object(network.sys, "platform", "linux")
    def test_status_distinguishes_errors_timeouts_and_absent_backend(self):
        self.config["devices"][0]["addresses"] = ["192.0.2.11"]
        plan = network.plan_status(self.config, ["fictional-lamp"])
        for side_effect, code, expected in (
            (None, 2, "error"), (OSError(), None, "error"),
            (subprocess.TimeoutExpired("ping", 2), None, "no_response"),
            (FileNotFoundError(), None, "unavailable"),
        ):
            self.run.side_effect = side_effect
            self.run.return_value = mock.Mock(returncode=code)
            self.assertEqual(network.run_status(self.config, plan, plan["id"])["devices"][0]["status"], expected)
        self.which.return_value = None
        self.run.reset_mock()
        self.assertEqual(network.run_status(self.config, plan, plan["id"])["devices"][0]["status"], "unavailable")
        self.run.assert_not_called()

    @mock.patch.object(network.sys, "platform", "darwin")
    def test_macos_no_reply_exit_code_and_ipv6_backend(self):
        self.config["devices"][0]["addresses"] = ["2001:db8::11"]
        plan = network.plan_status(self.config, ["fictional-lamp"])
        self.run.return_value = mock.Mock(returncode=2)
        self.assertEqual(network.run_status(self.config, plan, plan["id"])["devices"][0]["status"], "no_response")
        self.which.assert_called_once_with("ping6")

    def test_direct_wake_sends_exact_magic_packet_to_reviewed_endpoint(self):
        plan = network.plan_wake(self.config, "fictional-lamp")
        sender = self.socket.return_value.__enter__.return_value
        sender.sendto.return_value = 102
        result = network.run_wake(self.config, plan, plan["id"])
        sender.sendto.assert_called_once_with(b"\xff" * 6 + bytes.fromhex("020000000011") * 16, ("192.0.2.255", 9))
        sender.setsockopt.assert_called_once_with(network.socket.SOL_SOCKET, network.socket.SO_BROADCAST, 1)
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["power_state"], "unknown")
        self.run.assert_not_called()
        sender.sendto.side_effect = OSError("private implementation detail")
        result = network.run_wake(self.config, plan, plan["id"])
        self.assertEqual(result["status"], "error")
        self.assertNotIn("private", str(result))

    def test_relay_quotes_all_configured_arguments_and_reports_request_only(self):
        command = ["/opt/fictional tools/sender", "$(touch /tmp/not-executed)", "x'; printf bad", "02:00:00:00:00:11"]
        self.config["devices"][0].update(relay_host="operator@relay.example", relay_command=command)
        plan = network.plan_wake(self.config, "fictional-lamp")
        self.run.return_value = mock.Mock(returncode=0)
        result = network.run_wake(self.config, plan, plan["id"])
        call = self.run.call_args
        self.assertEqual(call.args[0][-2], "operator@relay.example")
        self.assertEqual(shlex.split(call.args[0][-1]), command)
        self.assertIn("-oBatchMode=yes", call.args[0])
        self.assertIn("-oStrictHostKeyChecking=yes", call.args[0])
        self.assertEqual(call.args[0][1:3], ["-F", "/dev/null"])
        self.assertNotIn("shell", call.kwargs)
        self.assertEqual(call.kwargs["timeout"], 10)
        self.assertEqual(result["status"], "requested")
        self.assertEqual(result["power_state"], "unknown")
        self.socket.assert_not_called()
        self.run.side_effect = subprocess.TimeoutExpired("ssh", 10)
        self.assertEqual(network.run_wake(self.config, plan, plan["id"])["status"], "unknown")
        self.which.return_value = None
        self.assertEqual(network.run_wake(self.config, plan, plan["id"])["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
