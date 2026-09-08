from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byte_core import cli, helpers_config


class HelpersConfigTests(unittest.TestCase):
    def test_defaults_are_independent_and_template_matches(self):
        first = helpers_config.load()
        first["shell"]["prompt"] = True
        self.assertFalse(helpers_config.load()["shell"]["prompt"])
        self.assertEqual(helpers_config.load(str(ROOT / "templates/helpers.toml")), helpers_config.load())

    def test_strict_schema_errors_omit_untrusted_values(self):
        invalid = [
            {}, {"schema_version": True}, {"schema_version": 2},
            {"schema_version": 1, "shell": {"prompt": "true"}},
            {"schema_version": 1, "shell": {"development_directory": "relative"}},
            {"schema_version": 1, "shell": {"development_directory": "/srv/../example"}},
            {"schema_version": 1, "shell": {"prompt_label": "example\x1b[0m"}},
            {"schema_version": 1, "assistant": {"executable": "./example"}},
            {"schema_version": 1, "assistant": {"executable": "/srv/../example"}},
            {"schema_version": 1, "assistant": {"new_args": "--project"}},
            {"schema_version": 1, "devices": [{"name": "example", "addresses": ["example.invalid"]}]},
            {"schema_version": 1, "devices": [{"name": "example", "relay_host": "-example"}]},
            {"schema_version": 1, "network": {"workers": True}},
            {"schema_version": 1, "network": {"ping_timeout": float("nan")}},
            {"schema_version": 1, "network": {"relay_timeout": 31}},
            {"schema_version": 1, "shell": {"highlighting": True}},
            {"schema_version": 1, "untrusted-marker": "do not repeat"},
        ]
        for document in invalid:
            with self.subTest(document=document):
                with self.assertRaises(helpers_config.HelperConfigError) as error:
                    helpers_config.validate(document)
                self.assertNotIn("untrusted-marker", str(error.exception))
                self.assertNotIn("do not repeat", str(error.exception))

    def test_literal_values_and_separate_arguments_are_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp).resolve() / "must-not-exist"
            config = helpers_config.validate({"schema_version": 1, "shell": {
                "prompt_label": f"$(touch {marker})"}, "assistant": {
                "executable": "example-assistant", "new_args": ["{project}", "a b", "$(false)"]}})
            self.assertFalse(marker.exists())
            self.assertEqual(helpers_config.get_scalar(config, "shell.prompt_label"), f"$(touch {marker})")
            self.assertEqual(config["assistant"]["new_args"][1], "a b")

    def test_missing_scalars_unknown_keys_and_duplicate_devices(self):
        for key in ("shell.development_directory", "assistant.executable", "shell.unrecognized"):
            with self.assertRaises(helpers_config.HelperConfigError):
                helpers_config.get_scalar(helpers_config.load(), key)
        with self.assertRaises(helpers_config.HelperConfigError):
            helpers_config.validate({"schema_version": 1, "devices": [{"name": "example"}] * 2})

    def test_bounded_regular_file_and_duplicate_toml_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "helpers.toml"
            path.write_text("schema_version = 1\nschema_version = 1\n")
            with self.assertRaises(helpers_config.HelperConfigError):
                helpers_config.load(str(path))
            path.write_bytes(b"#" * (2 * 1024 * 1024 + 1))
            with self.assertRaises(helpers_config.HelperConfigError):
                helpers_config.load(str(path))
            path.write_text("schema_version = 1\n")
            link = Path(tmp).resolve() / "link.toml"
            link.symlink_to(path)
            with self.assertRaises(helpers_config.HelperConfigError):
                helpers_config.load(str(link))
            with self.assertRaises(helpers_config.HelperConfigError):
                helpers_config.load("relative.toml")


class HelpersCliTests(unittest.TestCase):
    def invoke(self, args):
        output, errors = io.StringIO(), io.StringIO()
        code = cli.main(["helpers", *args], stdout=output, stderr=errors)
        return code, output.getvalue(), errors.getvalue()

    def test_config_selection_precedence_and_no_network_or_apps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "helpers.toml"
            path.write_text('schema_version = 1\n[shell]\nprompt_label = "Example"\n')
            with mock.patch.dict("os.environ", {"BYTE_CORE_HELPERS_CONFIG": str(path)}), \
                    mock.patch("subprocess.run", side_effect=AssertionError("must not execute")), \
                    mock.patch("socket.socket", side_effect=AssertionError("must not connect")):
                self.assertEqual(self.invoke(["config", "get", "shell.prompt_label"]), (0, "Example\n", ""))
                self.assertEqual(self.invoke(["--config", str(ROOT / "templates/helpers.toml"),
                                              "config", "get", "shell.prompt_label"]), (0, "Byte\n", ""))
                self.assertEqual(self.invoke(["config", "validate"])[0], 0)
                self.assertEqual(self.invoke(["config", "get", "shell.development_directory"])[0], 4)

    def test_example_is_available_even_with_invalid_config_selector(self):
        with mock.patch.dict("os.environ", {"BYTE_CORE_HELPERS_CONFIG": "invalid"}):
            self.assertEqual(self.invoke(["config", "example"]), (0, (ROOT / "templates/helpers.toml").read_text(), ""))

    def test_missing_assistant_is_actionable(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            code, _, error = self.invoke(["assistant", "new"])
            self.assertEqual(code, 4)
            self.assertNotIn("Traceback", error)
            self.assertIn("assistant", error.lower())

    def test_assistant_forwarding_and_exit_status(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch("byte_core.helper_shell.run_assistant", return_value=23) as launch:
            self.assertEqual(self.invoke(["assistant", "resume", "--", "a b", "--flag"])[0], 23)
            self.assertEqual(launch.call_args.args[1:], ("resume", ["a b", "--flag"]))

    def test_offline_wake_plan_and_host_gate_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp).resolve() / "helpers.toml"
            config.write_text('schema_version = 1\n[[devices]]\nname = "example"\nmac = "02:00:00:00:00:01"\nbroadcast = "192.0.2.255"\nport = 9\n')
            args = ["--config", str(config), "wakelan"]
            with mock.patch("socket.socket", side_effect=AssertionError("no network")):
                code, output, _ = self.invoke([*args, "plan", "--device", "example"])
                self.assertEqual(code, 0)
                plan = json.loads(output)
                saved = Path(tmp).resolve() / "plan.json"
                saved.write_text(output)
                with mock.patch("byte_core.cli.collect_check_report", return_value=SimpleNamespace(supported=False)):
                    self.assertEqual(self.invoke([*args, "run", "--plan", str(saved), "--approve", plan["id"]])[0], 3)
                with mock.patch("byte_core.cli.collect_check_report", return_value=SimpleNamespace(supported=True)):
                    self.assertEqual(self.invoke([*args, "run", "--plan", str(saved), "--approve", "wrong"])[0], 4)

    def test_wake_unknown_and_sync_partial_are_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp).resolve() / "plan.json"
            plan.write_text("{}")
            with mock.patch.dict("os.environ", {}, clear=True), \
                    mock.patch("byte_core.cli.collect_check_report", return_value=SimpleNamespace(supported=True)), \
                    mock.patch("byte_core.helper_network.run_wake", return_value={"kind": "wakelan_result", "status": "unknown"}):
                self.assertEqual(self.invoke(["wakelan", "run", "--plan", str(plan), "--approve", "example"])[0], 7)
            with mock.patch.dict("os.environ", {}, clear=True), \
                    mock.patch("byte_core.cli.collect_check_report", return_value=SimpleNamespace(supported=True)), \
                    mock.patch("byte_core.helper_sync.apply", return_value={"status": "partial"}):
                self.assertEqual(self.invoke(["canisync", "apply", "--plan", str(plan), "--approve", "example"])[0], 7)

    def test_malformed_plan_and_config_are_controlled_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "bad"
            path.write_text("not a document")
            with mock.patch.dict("os.environ", {}, clear=True):
                self.assertEqual(self.invoke(["--config", str(path), "config", "validate"])[0], 4)
                self.assertEqual(self.invoke(["wakelan", "run", "--plan", str(path), "--approve", "example"])[0], 4)


if __name__ == "__main__":
    unittest.main()
