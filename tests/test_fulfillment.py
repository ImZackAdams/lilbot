from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.fulfill_order import append_ledger, build_license_key, build_record, render_customer_email


class FulfillmentTests(unittest.TestCase):
    def test_build_license_key_matches_runtime_format(self) -> None:
        key = build_license_key("ORDER123CUSTOMER")

        self.assertTrue(key.startswith("LILBOT-PRO-"))
        self.assertEqual(len(key.rsplit("-", 1)[-1]), 8)

    def test_render_customer_email_contains_activation_commands(self) -> None:
        record = build_record(
            email="buyer@example.com",
            order_id="ORDER123",
            payload="ORDER123CUSTOMER",
        )
        text = render_customer_email(record)

        self.assertIn("Subject: Your Lilbot Pro license", text)
        self.assertIn("lilbot license activate", text)
        self.assertIn("buyer@example.com", text)
        self.assertIn("lilbot pro launch-pack", text)

    def test_append_ledger_writes_csv(self) -> None:
        record = build_record(
            email="buyer@example.com",
            order_id="ORDER123",
            payload="ORDER123CUSTOMER",
        )
        with tempfile.TemporaryDirectory() as tempdir:
            ledger = Path(tempdir) / "orders.csv"
            append_ledger(ledger, record)
            text = ledger.read_text(encoding="utf-8")

        self.assertIn("created_at,email,order_id,plan,license_key", text)
        self.assertIn("buyer@example.com", text)
