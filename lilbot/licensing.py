"""Local Pro entitlement helpers for Lilbot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any


LICENSE_KEY_ENV_VAR = "LILBOT_LICENSE_KEY"
LICENSE_EMAIL_ENV_VAR = "LILBOT_LICENSE_EMAIL"
LICENSE_PATH_ENV_VAR = "LILBOT_LICENSE_PATH"
CHECKOUT_URL_ENV_VAR = "LILBOT_CHECKOUT_URL"
SUPPORT_EMAIL_ENV_VAR = "LILBOT_SUPPORT_EMAIL"

DEFAULT_LICENSE_FILENAME = "license.json"
DEFAULT_PRO_PRICE = "$19/month per seat or $190/year"
DEFAULT_SUPPORT_EMAIL = "support@example.com"


@dataclass(frozen=True)
class LicenseStatus:
    """Current Lilbot product entitlement."""

    tier: str
    active: bool
    source: str
    message: str
    license_path: Path
    key_fingerprint: str | None = None
    email: str | None = None
    checkout_url: str | None = None
    support_email: str = DEFAULT_SUPPORT_EMAIL

    @property
    def tier_label(self) -> str:
        return "Pro" if self.active else "Free"


def default_license_path() -> Path:
    """Return the per-user Lilbot license path."""

    override = os.getenv(LICENSE_PATH_ENV_VAR)
    if override:
        return Path(override).expanduser()

    xdg_root = os.getenv("XDG_CONFIG_HOME")
    base_root = Path(xdg_root).expanduser() if xdg_root else Path.home() / ".config"
    return base_root / "lilbot" / DEFAULT_LICENSE_FILENAME


def load_license_status(path: str | Path | None = None) -> LicenseStatus:
    """Load the active Pro entitlement from environment or local activation file."""

    license_path = Path(path).expanduser() if path is not None else default_license_path()
    checkout_url = _checkout_url()
    support_email = os.getenv(SUPPORT_EMAIL_ENV_VAR, DEFAULT_SUPPORT_EMAIL).strip() or DEFAULT_SUPPORT_EMAIL

    env_key = _coerce_text(os.getenv(LICENSE_KEY_ENV_VAR))
    if env_key:
        email = _coerce_text(os.getenv(LICENSE_EMAIL_ENV_VAR))
        return _evaluate_license_key(
            env_key,
            source=LICENSE_KEY_ENV_VAR,
            license_path=license_path,
            email=email,
            checkout_url=checkout_url,
            support_email=support_email,
        )

    if not license_path.exists():
        return LicenseStatus(
            tier="free",
            active=False,
            source="none",
            message="No Pro license is active.",
            license_path=license_path,
            checkout_url=checkout_url,
            support_email=support_email,
        )

    try:
        raw_text = license_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text or "{}")
    except (OSError, json.JSONDecodeError) as exc:
        return LicenseStatus(
            tier="free",
            active=False,
            source=str(license_path),
            message=f"License file could not be read: {exc}",
            license_path=license_path,
            checkout_url=checkout_url,
            support_email=support_email,
        )

    if not isinstance(payload, dict):
        return LicenseStatus(
            tier="free",
            active=False,
            source=str(license_path),
            message="License file must contain a JSON object.",
            license_path=license_path,
            checkout_url=checkout_url,
            support_email=support_email,
        )

    stored_key = _coerce_text(payload.get("license_key"))
    stored_email = _coerce_text(payload.get("email"))
    if not stored_key:
        return LicenseStatus(
            tier="free",
            active=False,
            source=str(license_path),
            message="License file does not contain a license key.",
            license_path=license_path,
            checkout_url=checkout_url,
            support_email=support_email,
        )

    return _evaluate_license_key(
        stored_key,
        source=str(license_path),
        license_path=license_path,
        email=stored_email,
        checkout_url=checkout_url,
        support_email=support_email,
    )


def activate_license_key(
    license_key: str,
    *,
    email: str | None = None,
    path: str | Path | None = None,
) -> LicenseStatus:
    """Validate and persist a Pro license key for the current user."""

    license_path = Path(path).expanduser() if path is not None else default_license_path()
    status = _evaluate_license_key(
        license_key,
        source="activation",
        license_path=license_path,
        email=_coerce_text(email),
        checkout_url=_checkout_url(),
        support_email=os.getenv(SUPPORT_EMAIL_ENV_VAR, DEFAULT_SUPPORT_EMAIL),
    )
    if not status.active:
        raise ValueError(status.message)

    values: dict[str, Any] = {
        "license_key": _format_license_key(license_key),
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    if status.email:
        values["email"] = status.email

    try:
        license_path.parent.mkdir(parents=True, exist_ok=True)
        license_path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not write Lilbot license to {license_path}: {exc}") from exc

    return load_license_status(license_path)


def render_license_status(status: LicenseStatus | None = None) -> str:
    """Render a customer-facing license status message."""

    status = status or load_license_status()
    lines = [
        "Lilbot license",
        f"- tier: {status.tier_label}",
        f"- source: {status.source}",
        f"- license_file: {status.license_path}",
        f"- status: {status.message}",
    ]
    if status.key_fingerprint:
        lines.append(f"- key: {status.key_fingerprint}")
    if status.email:
        lines.append(f"- email: {status.email}")
    if not status.active:
        lines.append(f"- upgrade: {_checkout_text(status.checkout_url)}")
        lines.append("- activate: lilbot license activate <license-key>")
    return "\n".join(lines)


def render_pricing(status: LicenseStatus | None = None) -> str:
    """Render pricing and purchase instructions for the CLI."""

    status = status or load_license_status()
    lines = [
        "Lilbot pricing",
        "",
        "Free",
        "- local chat with your configured model",
        "- deterministic repository, log, shell-explanation, and system-inspection commands",
        "- local-first safety controls and setup diagnostics",
        "",
        f"Pro - {DEFAULT_PRO_PRICE}",
        "- product readiness audits for repositories",
        "- monetization, release, support, and packaging gap analysis",
        "- Pro audit tool access inside the agent tool registry",
        "",
        "Checkout",
        f"- {_checkout_text(status.checkout_url)}",
        "",
        "After purchase",
        "- lilbot license activate <license-key>",
        "- lilbot pro audit .",
    ]
    if status.active:
        lines.extend(["", "Current license", f"- tier: {status.tier_label}"])
    return "\n".join(lines)


def render_upgrade_required(feature: str, status: LicenseStatus | None = None) -> str:
    """Render an upgrade prompt for a gated Pro feature."""

    status = status or load_license_status()
    return "\n".join(
        [
            f"{feature} is available in Lilbot Pro.",
            f"Current tier: {status.tier_label}",
            f"Upgrade: {_checkout_text(status.checkout_url)}",
            "Activate after purchase: lilbot license activate <license-key>",
            "Free commands remain available: doctor, self-test, repo summarize, logs analyze, and explain-command.",
        ]
    )


def _evaluate_license_key(
    license_key: str,
    *,
    source: str,
    license_path: Path,
    email: str | None,
    checkout_url: str | None,
    support_email: str,
) -> LicenseStatus:
    formatted = _format_license_key(license_key)
    valid, message = _is_valid_license_key(formatted)
    if not valid:
        return LicenseStatus(
            tier="free",
            active=False,
            source=source,
            message=message,
            license_path=license_path,
            checkout_url=checkout_url,
            support_email=support_email,
        )

    return LicenseStatus(
        tier="pro",
        active=True,
        source=source,
        message="Pro license is active.",
        license_path=license_path,
        key_fingerprint=_fingerprint_key(formatted),
        email=email,
        checkout_url=checkout_url,
        support_email=support_email,
    )


def _is_valid_license_key(license_key: str) -> tuple[bool, str]:
    parts = license_key.split("-")
    if len(parts) < 4 or parts[0] != "LILBOT" or parts[1] != "PRO":
        return False, "License key must use the LILBOT-PRO-... format."

    payload = "".join(parts[2:-1])
    checksum = parts[-1]
    if len(payload) < 12 or not payload.isalnum():
        return False, "License key payload is incomplete."
    if len(checksum) != 8 or not all(char in "0123456789ABCDEF" for char in checksum):
        return False, "License key checksum is malformed."

    expected = _license_checksum(payload)
    if not hmac.compare_digest(checksum, expected):
        return False, "License key checksum is invalid."
    return True, "Pro license is active."


def _license_checksum(payload: str) -> str:
    normalized = "".join(char for char in payload.upper() if char.isalnum())
    digest = hashlib.sha256(f"lilbot-pro:{normalized}".encode("utf-8")).hexdigest()
    return digest[:8].upper()


def _format_license_key(license_key: str) -> str:
    text = str(license_key).strip().upper().replace("_", "-")
    groups = [group for group in text.split("-") if group]
    return "-".join(groups)


def _fingerprint_key(license_key: str) -> str:
    compact = license_key.replace("-", "")
    if len(compact) <= 12:
        return compact
    return f"{compact[:8]}...{compact[-4:]}"


def _checkout_url() -> str | None:
    value = _coerce_text(os.getenv(CHECKOUT_URL_ENV_VAR))
    return value


def _checkout_text(checkout_url: str | None) -> str:
    if checkout_url:
        return checkout_url
    return "set LILBOT_CHECKOUT_URL to your Stripe Payment Link, Gumroad product, or billing page"


def _coerce_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
