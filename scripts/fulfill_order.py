#!/usr/bin/env python3
"""Fulfill a Lilbot Pro order with a license key and customer email."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import secrets
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lilbot.licensing import _license_checksum  # noqa: E402


@dataclass(frozen=True)
class FulfillmentRecord:
    email: str
    license_key: str
    order_id: str
    plan: str
    created_at: str


def build_license_key(payload: str | None = None) -> str:
    normalized = _normalize_payload(payload or secrets.token_hex(8).upper())
    return f"LILBOT-PRO-{'-'.join(_chunks(normalized, 4))}-{_license_checksum(normalized)}"


def build_record(
    *,
    email: str,
    plan: str = "Pro",
    order_id: str | None = None,
    payload: str | None = None,
) -> FulfillmentRecord:
    clean_email = email.strip()
    if "@" not in clean_email:
        raise ValueError("Customer email is required for fulfillment.")
    clean_order_id = (order_id or "manual").strip() or "manual"
    created_at = datetime.now(timezone.utc).isoformat()
    key_payload = payload or f"{clean_order_id}{clean_email.split('@', 1)[0]}"
    return FulfillmentRecord(
        email=clean_email,
        license_key=build_license_key(key_payload),
        order_id=clean_order_id,
        plan=plan.strip() or "Pro",
        created_at=created_at,
    )


def render_customer_email(record: FulfillmentRecord) -> str:
    return "\n".join(
        [
            f"Subject: Your Lilbot {record.plan} license",
            "",
            "Thanks for purchasing Lilbot Pro.",
            "",
            "Activate your license with:",
            "",
            "```bash",
            f"lilbot license activate {record.license_key} --email {record.email}",
            "lilbot license status",
            "lilbot pro audit .",
            "lilbot pro launch-pack . --output lilbot-launch-pack.md",
            "```",
            "",
            "If activation fails, reply with the output of:",
            "",
            "```bash",
            "lilbot --version",
            "lilbot doctor",
            "lilbot license status",
            "```",
        ]
    )


def append_ledger(path: Path, record: FulfillmentRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("created_at", "email", "order_id", "plan", "license_key"),
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "created_at": record.created_at,
                "email": record.email,
                "order_id": record.order_id,
                "plan": record.plan,
                "license_key": record.license_key,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fulfill a paid Lilbot Pro order.")
    parser.add_argument("--email", required=True, help="Customer email address.")
    parser.add_argument("--order-id", default=None, help="Payment provider order id.")
    parser.add_argument("--plan", default="Pro", help="Purchased plan label.")
    parser.add_argument("--payload", default=None, help="Optional deterministic key payload.")
    parser.add_argument("--ledger", default=None, help="Optional CSV path for a local fulfillment ledger.")
    args = parser.parse_args()

    try:
        record = build_record(
            email=args.email,
            plan=args.plan,
            order_id=args.order_id,
            payload=args.payload,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.ledger:
        append_ledger(Path(args.ledger).expanduser(), record)

    print(render_customer_email(record))
    if args.ledger:
        print("")
        print(f"Ledger updated: {Path(args.ledger).expanduser()}")


def _normalize_payload(value: str) -> str:
    payload = "".join(char for char in value.upper() if char.isalnum())
    if len(payload) < 12:
        raise ValueError("Payload must contain at least 12 letters or digits.")
    return payload


def _chunks(value: str, size: int) -> list[str]:
    return [value[index : index + size] for index in range(0, len(value), size)]


if __name__ == "__main__":
    main()
