from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from byte_core.configuration import (  # noqa: E402
    ConfigurationError,
    Layer,
    resolve_configuration,
    resolve_workspace_path,
)

FIXTURES = Path(__file__).parent / "fixtures" / "configuration"
VALID = FIXTURES / "valid"
INVALID = FIXTURES / "invalid"


class ConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = self._fixture_hashes()

    def tearDown(self) -> None:
        self.assertEqual(self.before, self._fixture_hashes())

    def test_resolves_four_layers_with_documented_precedence(self) -> None:
        result = resolve_configuration(
            [
                Layer("host", VALID / "host.toml"),
                Layer("core", VALID / "core.toml"),
                Layer("platform", VALID / "platform.toml"),
                Layer("deployment", VALID / "deployment.toml"),
            ]
        )

        self.assertEqual(result.schema_version, 1)
        self.assertEqual(
            result.values,
            {
                "deployment": {
                    "name": "example-deployment",
                    "domain": "example.test",
                    "tags": ["host"],
                },
                "selection": {
                    "platform": "example-platform",
                    "host": "node-42.example",
                },
                "paths": {
                    "workspace": "deployment-data",
                },
                "retention": {
                    "cache_days": 3,
                },
            },
        )

    def test_reports_source_attribution_for_resolved_values(self) -> None:
        result = resolve_configuration(self._valid_layers())

        expected_sources = {
            "deployment.name": "deployment",
            "deployment.domain": "core",
            "deployment.tags": "host",
            "selection.platform": "platform",
            "selection.host": "host",
            "paths.workspace": "deployment",
            "retention.cache_days": "platform",
        }

        self.assertEqual(result.sources, expected_sources)
        self.assertEqual(
            result.source_for("deployment.domain"),
            "core",
        )

    def test_rejects_unknown_keys(self) -> None:
        error = self._resolve_with_invalid(
            "deployment",
            "unknown-key.toml",
        )

        self.assertEqual(error.code, "unknown_key")
        self.assertEqual(error.layer, "deployment")
        self.assertEqual(error.key, "deployment.owner")

    def test_rejects_type_mismatches(self) -> None:
        error = self._resolve_with_invalid(
            "deployment",
            "type-mismatch.toml",
        )

        self.assertEqual(error.code, "type_mismatch")
        self.assertEqual(error.layer, "deployment")
        self.assertEqual(error.key, "retention.cache_days")
        self.assertNotIn("seven", str(error))

    def test_rejects_future_core_schema(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            resolve_configuration(
                [
                    Layer(
                        "core",
                        INVALID / "future-schema.toml",
                    )
                ]
            )

        self.assertEqual(
            raised.exception.code,
            "unsupported_schema_version",
        )
        self.assertEqual(raised.exception.layer, "core")
        self.assertEqual(
            raised.exception.key,
            "schema_version",
        )

    def test_rejects_mismatched_participating_schema(self) -> None:
        error = self._resolve_with_invalid(
            "host",
            "mismatched-schema.toml",
        )

        self.assertEqual(
            error.code,
            "schema_version_mismatch",
        )
        self.assertEqual(error.layer, "host")
        self.assertEqual(error.key, "schema_version")

    def test_rejects_nonpositive_schema(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            resolve_configuration(
                [
                    Layer(
                        "core",
                        INVALID / "nonpositive-schema.toml",
                    )
                ]
            )

        self.assertEqual(
            raised.exception.code,
            "invalid_schema_version",
        )

    def test_rejects_missing_core_layer(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            resolve_configuration(
                [
                    Layer(
                        "deployment",
                        VALID / "deployment.toml",
                    )
                ]
            )

        self.assertEqual(
            raised.exception.code,
            "missing_core_layer",
        )

    def test_rejects_duplicate_layers_before_reading(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            resolve_configuration(
                [
                    Layer("core", VALID / "core.toml"),
                    Layer("core", VALID / "core.toml"),
                ]
            )

        self.assertEqual(
            raised.exception.code,
            "duplicate_layer",
        )

    def test_errors_do_not_include_file_paths(self) -> None:
        path = INVALID / "type-mismatch.toml"
        error = self._resolve_with_invalid(
            "deployment",
            path.name,
        )

        self.assertNotIn(str(path), str(error))

    def test_workspace_paths_reject_escaping_and_expansion_in_every_layer(self) -> None:
        invalid = ("", "/absolute", "../outside", "inside/../outside", "./inside", "inside//nested",
                   "inside/", "~/inside", "inside/~user", "$HOME/inside", "${ROOT}/inside",
                   "%ROOT%/inside", "`pwd`/inside", "C:/inside", "C:inside", "inside\\nested",
                   "inside\x00nested", "inside\nnext", "inside\x7fnext")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            bad = root / "layer.toml"
            for value in invalid:
                with self.subTest(value=value):
                    bad.write_text('schema_version = 1\n[paths]\nworkspace = ' + json.dumps(value) + '\n')
                    with self.assertRaises(ConfigurationError) as raised:
                        resolve_configuration([Layer("core", bad), Layer("host", VALID / "host.toml")])
                    self.assertEqual(raised.exception.code, "invalid_workspace_path")
                    if value:
                        self.assertNotIn(value, str(raised.exception))

    def test_workspace_resolution_is_explicit_contained_and_does_not_create(self) -> None:
        config = resolve_configuration([Layer("core", VALID / "core.toml")])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual(resolve_workspace_path(config, root), root / "workspace")
            self.assertEqual(list(root.iterdir()), [])
            (root / "workspace").mkdir()
            self.assertEqual(resolve_workspace_path(config, root), root / "workspace")
            with self.assertRaises(ConfigurationError):
                resolve_workspace_path(config, root / "missing")
            with self.assertRaises(ConfigurationError):
                resolve_workspace_path(config, "relative")

    def test_workspace_resolution_rejects_symlinks_and_files(self) -> None:
        config = resolve_configuration([Layer("core", VALID / "core.toml")])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            deployment = root / "deployment"
            deployment.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (deployment / "workspace").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ConfigurationError):
                resolve_workspace_path(config, deployment)
            (deployment / "workspace").unlink()
            (deployment / "workspace").write_text("fictional sentinel")
            with self.assertRaises(ConfigurationError):
                resolve_workspace_path(config, deployment)
            self.assertEqual((deployment / "workspace").read_text(), "fictional sentinel")
            alias = root / "alias"
            alias.symlink_to(deployment, target_is_directory=True)
            with self.assertRaises(ConfigurationError):
                resolve_workspace_path(config, alias)

    def test_workspace_resolution_revalidates_mutated_values(self) -> None:
        config = resolve_configuration([Layer("core", VALID / "core.toml")])
        config.values["paths"]["workspace"] = "../changed"
        with mock.patch("pathlib.Path.is_dir", side_effect=AssertionError("validate before filesystem inspection")):
            with self.assertRaises(ConfigurationError):
                resolve_workspace_path(config, "/fictional/deployment")

    def _valid_layers(self) -> list[Layer]:
        return [
            Layer("core", VALID / "core.toml"),
            Layer("deployment", VALID / "deployment.toml"),
            Layer("platform", VALID / "platform.toml"),
            Layer("host", VALID / "host.toml"),
        ]

    def _resolve_with_invalid(
        self,
        layer_name: str,
        fixture_name: str,
    ) -> ConfigurationError:
        layers = [
            layer
            for layer in self._valid_layers()
            if layer.name != layer_name
        ]
        layers.append(
            Layer(layer_name, INVALID / fixture_name)
        )

        with self.assertRaises(ConfigurationError) as raised:
            resolve_configuration(layers)

        return raised.exception

    def _fixture_hashes(self) -> dict[Path, str]:
        return {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(FIXTURES.rglob("*.toml"))
        }


if __name__ == "__main__":
    unittest.main()
