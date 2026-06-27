from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lilbot.licensing import (
    _license_checksum,
    activate_license_key,
    load_license_status,
    render_pricing,
    start_trial,
)


def pro_key(payload: str = "CUSTOMER202606") -> str:
    return f"LILBOT-PRO-{payload}-{_license_checksum(payload)}"


class LicensingTests(unittest.TestCase):
    def test_activate_license_persists_pro_status(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            license_path = Path(tempdir) / "license.json"
            with patch.dict(os.environ, {"LILBOT_LICENSE_PATH": str(license_path)}, clear=True):
                before = load_license_status()
                self.assertFalse(before.active)

                activated = activate_license_key(pro_key(), email="buyer@example.com")
                loaded = load_license_status()

            self.assertTrue(activated.active)
            self.assertTrue(loaded.active)
            self.assertEqual(loaded.email, "buyer@example.com")
            self.assertTrue(license_path.is_file())

    def test_invalid_license_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            license_path = Path(tempdir) / "license.json"
            with patch.dict(os.environ, {"LILBOT_LICENSE_PATH": str(license_path)}, clear=True):
                with self.assertRaises(ValueError):
                    activate_license_key("LILBOT-PRO-CUSTOMER202606-00000000")

                status = load_license_status()

            self.assertFalse(status.active)

    def test_environment_license_overrides_license_file(self) -> None:
        key = pro_key("ENVBUYER202606")
        with tempfile.TemporaryDirectory() as tempdir:
            env = {
                "LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json"),
                "LILBOT_LICENSE_KEY": key,
                "LILBOT_LICENSE_EMAIL": "env-buyer@example.com",
            }
            with patch.dict(os.environ, env, clear=True):
                status = load_license_status()

        self.assertTrue(status.active)
        self.assertEqual(status.email, "env-buyer@example.com")
        self.assertEqual(status.source, "LILBOT_LICENSE_KEY")

    def test_pricing_mentions_checkout_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            env = {
                "LILBOT_LICENSE_PATH": str(Path(tempdir) / "license.json"),
                "LILBOT_CHECKOUT_URL": "https://billing.example/lilbot-pro",
            }
            with patch.dict(os.environ, env, clear=True):
                text = render_pricing()

        self.assertIn("Lilbot pricing", text)
        self.assertIn("https://billing.example/lilbot-pro", text)

    def test_start_trial_enables_trial_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            license_path = Path(tempdir) / "license.json"
            with patch.dict(os.environ, {"LILBOT_LICENSE_PATH": str(license_path)}, clear=True):
                status = start_trial(days=7)
                loaded = load_license_status()

        self.assertTrue(status.active)
        self.assertEqual(status.tier_label, "Trial")
        self.assertTrue(loaded.active)
        self.assertEqual(loaded.tier, "trial")
