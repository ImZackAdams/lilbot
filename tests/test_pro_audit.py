from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lilbot.config import LilbotConfig
from lilbot.licensing import _license_checksum
from lilbot.tools import build_default_tool_registry
from lilbot.tools.pro import render_launch_pack


def pro_key(payload: str = "AUDITBUYER202606") -> str:
    return f"LILBOT-PRO-{payload}-{_license_checksum(payload)}"


class ProAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / "README.md").write_text(
            "\n".join(
                [
                    "# Revenue Tool",
                    "",
                    "Revenue Tool helps developers package a local CLI product.",
                    "Quick Start",
                    "Install it, run the doctor command, review pricing, and activate Pro.",
                    "The Pro workflow includes checkout, license activate, and product audits.",
                ]
            )
            * 8,
            encoding="utf-8",
        )
        (self.workspace / "pyproject.toml").write_text("[project]\nname = 'revenue-tool'\n", encoding="utf-8")
        (self.workspace / "LICENSE").write_text("MIT\n", encoding="utf-8")
        (self.workspace / "CUSTOMER_TERMS.md").write_text("Paid support and refunds.\n", encoding="utf-8")
        (self.workspace / "SUPPORT.md").write_text("Support promise.\n", encoding="utf-8")
        (self.workspace / "PRIVACY.md").write_text("Local-first privacy.\n", encoding="utf-8")
        (self.workspace / ".env.example").write_text("LILBOT_CHECKOUT_URL=\n", encoding="utf-8")
        (self.workspace / "tests").mkdir()
        for index in range(4):
            (self.workspace / "tests" / f"test_{index}.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        (self.workspace / "ROADMAP.md").write_text("Ship paid audits.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_product_readiness_tool_requires_pro_license(self) -> None:
        config = LilbotConfig.from_sources(workspace_root=self.tempdir.name)
        registry = build_default_tool_registry(config)

        with tempfile.TemporaryDirectory() as tempdir:
            env = {"LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json")}
            with patch.dict(os.environ, env, clear=True):
                text = registry.execute("product_readiness_audit", {"path": "."})

        self.assertIn("available in Lilbot Pro", text)
        self.assertIn("lilbot license activate", text)

    def test_product_readiness_tool_renders_audit_for_pro_license(self) -> None:
        config = LilbotConfig.from_sources(workspace_root=self.tempdir.name)
        registry = build_default_tool_registry(config)

        with tempfile.TemporaryDirectory() as tempdir:
            env = {
                "LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json"),
                "LILBOT_LICENSE_KEY": pro_key(),
            }
            with patch.dict(os.environ, env, clear=True):
                text = registry.execute("product_readiness_audit", {"path": "."})

        self.assertIn("Lilbot Pro product readiness audit", text)
        self.assertIn("Findings", text)
        self.assertIn("[PASS] Monetization", text)
        self.assertIn("[PASS] Legal", text)
        self.assertIn("[PASS] Support", text)

    def test_launch_pack_renders_customer_ready_sections(self) -> None:
        config = LilbotConfig.from_sources(workspace_root=self.tempdir.name)

        text = render_launch_pack(config, ".")

        self.assertIn("# Revenue Tool Launch Pack", text)
        self.assertIn("## Paid Offer", text)
        self.assertIn("## Fulfillment Email", text)
        self.assertIn("lilbot pro launch-pack", text)
