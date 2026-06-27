from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from lilbot.cli import main
from lilbot.licensing import _license_checksum
from lilbot.model.base import BaseModel
from lilbot.onboarding import SelfTestCheck, SelfTestResult


class FakeModel(BaseModel):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.runtime_summary = "Loaded fake model on cpu"
        self.load_warnings: list[str] = []
        self.device = "cpu"
        self.quantization_active = False
        self.model_name = "fake-model"

    def generate(self, prompt: str) -> str:
        del prompt
        return self.outputs.pop(0)


class CliTests(unittest.TestCase):
    def _pro_key(self, payload: str = "CLIBUYER202606") -> str:
        return f"LILBOT-PRO-{payload}-{_license_checksum(payload)}"

    def test_one_shot_query_still_works(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.build_model", return_value=FakeModel(["FINAL: Ready."])),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["what is lilbot?"])

        self.assertIn("Ready.", stdout.getvalue())
        self.assertIn("Loaded fake model on cpu", stderr.getvalue())

    def test_no_args_starts_interactive_loop(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch(
                "lilbot.cli.build_model",
                return_value=FakeModel(["THOUGHT: answer\nFINAL: Lilbot is ready."]),
            ),
            patch("builtins.input", side_effect=["what is lilbot?", "exit"]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main([])

        text = stdout.getvalue()
        self.assertIn("Lilbot interactive mode", text)
        self.assertIn("Lilbot is ready.", text)
        self.assertIn("Leaving Lilbot.", text)
        self.assertIn("Loaded fake model on cpu", stderr.getvalue())

    def test_interactive_slash_commands_show_help_and_status(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.build_model", return_value=FakeModel([])),
            patch("builtins.input", side_effect=["/help", "/status", "exit"]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main([])

        text = stdout.getvalue()
        self.assertIn("Interactive commands:", text)
        self.assertIn("Workspace:", text)
        self.assertIn("Conversation turns: 0", text)

    def test_doctor_command_prints_report(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(["doctor"])

        text = stdout.getvalue()
        self.assertIn("Lilbot doctor", text)
        self.assertIn("Configuration", text)
        self.assertIn("Next steps", text)

    def test_self_test_command_prints_report(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = SelfTestResult(
            checks=(
                SelfTestCheck("config", "PASS", "config ok"),
                SelfTestCheck("tooling", "WARN", "tool warning"),
            )
        )

        with (
            patch("lilbot.cli.run_self_test", return_value=result),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["self-test"])

        text = stdout.getvalue()
        self.assertIn("Lilbot self-test", text)
        self.assertIn("[PASS] config", text)
        self.assertIn("[WARN] tooling", text)

    def test_self_test_exits_nonzero_on_failures(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = SelfTestResult(
            checks=(
                SelfTestCheck("imports", "FAIL", "missing runtime"),
            )
        )

        with self.assertRaises(SystemExit) as exit_info:
            with (
                patch("lilbot.cli.run_self_test", return_value=result),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["self-test"])

        self.assertEqual(exit_info.exception.code, 1)
        self.assertIn("[FAIL] imports", stdout.getvalue())

    def test_version_flag_prints_package_version(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as exit_info:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                main(["--version"])

        self.assertEqual(exit_info.exception.code, 0)
        self.assertIn("lilbot", stdout.getvalue())

    def test_init_command_writes_user_config(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.json"
            with (
                patch.dict(os.environ, {"LILBOT_CONFIG_PATH": str(config_path)}, clear=True),
                patch("builtins.input", side_effect=["", "none", "cpu", "", "", ""]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["init"])

            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["device"], "cpu")
            self.assertFalse(saved["quantize_4bit"])
            self.assertIn("workspace_root", saved)
            self.assertIn("Saved Lilbot config", stdout.getvalue())

    def test_init_without_model_explains_partial_setup(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.json"
            with (
                patch.dict(os.environ, {"LILBOT_CONFIG_PATH": str(config_path)}, clear=True),
                patch("lilbot.config.discover_default_model", return_value=None),
                patch("lilbot.onboarding.discover_default_model", return_value=None),
                patch("builtins.input", side_effect=["", "", "cpu", "", "", ""]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["init"])

            text = stdout.getvalue()
            self.assertIn("Lilbot is not ready for AI chat yet", text)
            self.assertIn("Deterministic commands", text)

    def test_pricing_command_prints_purchase_path(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            env = {
                "LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json"),
                "LILBOT_CHECKOUT_URL": "https://billing.example/lilbot-pro",
            }
            with (
                patch.dict(os.environ, env, clear=True),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["pricing"])

        text = stdout.getvalue()
        self.assertIn("Lilbot pricing", text)
        self.assertIn("https://billing.example/lilbot-pro", text)

    def test_license_activate_command_writes_license(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            license_path = Path(tempdir) / "license.json"
            with (
                patch.dict(os.environ, {"LILBOT_LICENSE_PATH": str(license_path)}, clear=True),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["license", "activate", self._pro_key(), "--email", "cli@example.com"])

            self.assertTrue(license_path.is_file())

        text = stdout.getvalue()
        self.assertIn("Lilbot Pro activated.", text)
        self.assertIn("tier: Pro", text)

    def test_pro_audit_command_requires_license(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            workspace = Path(tempdir) / "workspace"
            workspace.mkdir()
            with (
                patch.dict(os.environ, {"LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json")}, clear=True),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["--workspace-root", str(workspace), "pro", "audit", "."])

        self.assertIn("available in Lilbot Pro", stdout.getvalue())

    def test_pro_launch_pack_command_writes_markdown_for_pro_license(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            workspace = Path(tempdir) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text(
                "# Launchable CLI\n\nA local-first CLI product for developers who need launch readiness.\n",
                encoding="utf-8",
            )
            output_path = workspace / "launch-pack.md"
            env = {
                "LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json"),
                "LILBOT_LICENSE_KEY": self._pro_key("LAUNCHBUYER2026"),
            }
            with (
                patch.dict(os.environ, env, clear=True),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(
                    [
                        "--workspace-root",
                        str(workspace),
                        "pro",
                        "launch-pack",
                        ".",
                        "--output",
                        "launch-pack.md",
                    ]
                )

            written = output_path.read_text(encoding="utf-8")

        self.assertIn("Wrote Lilbot Pro launch pack", stdout.getvalue())
        self.assertIn("# Launchable CLI Launch Pack", written)
        self.assertIn("## Checkout Copy", written)
