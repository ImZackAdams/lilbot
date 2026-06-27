#!/usr/bin/env python3
"""Issue Lilbot Pro license keys for paid checkout fulfillment."""

from __future__ import annotations

import argparse
from pathlib import Path
import secrets
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lilbot.licensing import _license_checksum  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a Lilbot Pro license key.")
    parser.add_argument(
        "--payload",
        default=None,
        help="Optional buyer/order payload. Defaults to a random token.",
    )
    parser.add_argument(
        "--prefix",
        default="LILBOT-PRO",
        help="License key prefix. Keep the default for Lilbot Pro.",
    )
    args = parser.parse_args()

    payload = _normalize_payload(args.payload or secrets.token_hex(8).upper())
    checksum = _license_checksum(payload)
    grouped_payload = "-".join(_chunks(payload, 4))
    print(f"{args.prefix.upper()}-{grouped_payload}-{checksum}")


def _normalize_payload(value: str) -> str:
    payload = "".join(char for char in value.upper() if char.isalnum())
    if len(payload) < 12:
        raise SystemExit("Payload must contain at least 12 letters or digits.")
    return payload


def _chunks(value: str, size: int) -> list[str]:
    return [value[index : index + size] for index in range(0, len(value), size)]


if __name__ == "__main__":
    main()
