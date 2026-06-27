#!/usr/bin/env python3
"""Run launch-readiness checks for Lilbot Pro."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import sys


PLACEHOLDER_CHECKOUT_URL = "https://example.com/lilbot-pro-checkout"


@dataclass(frozen=True)
class LaunchCheck:
    name: str
    status: str
    detail: str


def run_checks(root: Path) -> list[LaunchCheck]:
    root = root.resolve()
    checks = [
        _required_files(root),
        _paid_docs(root),
        _checkout_configuration(root),
        _pro_cli_surface(root),
        _license_fulfillment(root),
        _test_coverage(root),
        _ci_configuration(root),
    ]
    return [check for group in checks for check in group]


def render_report(checks: list[LaunchCheck]) -> str:
    failures = sum(1 for check in checks if check.status == "FAIL")
    warnings = sum(1 for check in checks if check.status == "WARN")
    passes = sum(1 for check in checks if check.status == "PASS")
    overall = "FAIL" if failures else "WARN" if warnings else "PASS"

    lines = ["Lilbot Pro launch check", ""]
    for check in checks:
        lines.append(f"[{check.status}] {check.name}: {check.detail}")
    lines.extend(
        [
            "",
            "Summary",
            f"- status: {overall}",
            f"- passes: {passes}",
            f"- warnings: {warnings}",
            f"- failures: {failures}",
        ]
    )
    if warnings and not failures:
        lines.extend(
            [
                "",
                "Launch note",
                "- Warnings are allowed for private testing, but resolve checkout placeholders before public promotion.",
            ]
        )
    return "\n".join(lines)


def exit_code(checks: list[LaunchCheck]) -> int:
    return 1 if any(check.status == "FAIL" for check in checks) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lilbot Pro launch-readiness checks.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()

    checks = run_checks(Path(args.root))
    print(render_report(checks))
    raise SystemExit(exit_code(checks))


def _required_files(root: Path) -> list[LaunchCheck]:
    required = [
        "README.md",
        "MONETIZATION.md",
        "pyproject.toml",
        "lilbot/cli.py",
        "lilbot/licensing.py",
        "lilbot/tools/pro.py",
        "site/index.html",
        "site/styles.css",
    ]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        return [LaunchCheck("Required files", "FAIL", "Missing: " + ", ".join(missing))]
    return [LaunchCheck("Required files", "PASS", "Product, pricing, licensing, and site files are present.")]


def _paid_docs(root: Path) -> list[LaunchCheck]:
    required = ["CUSTOMER_TERMS.md", "SUPPORT.md", "PRIVACY.md"]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        return [LaunchCheck("Paid docs", "FAIL", "Missing: " + ", ".join(missing))]
    return [LaunchCheck("Paid docs", "PASS", "Customer terms, support policy, and privacy notes are present.")]


def _checkout_configuration(root: Path) -> list[LaunchCheck]:
    site_path = root / "site" / "index.html"
    env_path = root / ".env.example"
    checkout_url = os.getenv("LILBOT_CHECKOUT_URL", "").strip()
    site_text = _read_text(site_path)
    env_text = _read_text(env_path)

    if "LILBOT_CHECKOUT_URL" not in env_text:
        return [LaunchCheck("Checkout configuration", "FAIL", ".env.example does not document LILBOT_CHECKOUT_URL.")]
    if checkout_url and checkout_url != PLACEHOLDER_CHECKOUT_URL and PLACEHOLDER_CHECKOUT_URL not in site_text:
        return [LaunchCheck("Checkout configuration", "PASS", "Runtime checkout URL is set and the sales page placeholder is gone.")]
    if PLACEHOLDER_CHECKOUT_URL in site_text:
        return [LaunchCheck("Checkout configuration", "WARN", "Sales page still contains the placeholder Pro checkout URL.")]
    return [LaunchCheck("Checkout configuration", "WARN", "Set LILBOT_CHECKOUT_URL before public promotion.")]


def _pro_cli_surface(root: Path) -> list[LaunchCheck]:
    cli_text = _read_text(root / "lilbot" / "cli.py")
    pro_text = _read_text(root / "lilbot" / "tools" / "pro.py")
    required_terms = ["pricing", "license", "pro", "audit", "launch-pack"]
    missing = [term for term in required_terms if term not in cli_text]
    if "render_launch_pack" not in pro_text:
        missing.append("render_launch_pack")
    if missing:
        return [LaunchCheck("Pro CLI surface", "FAIL", "Missing command terms: " + ", ".join(missing))]
    return [LaunchCheck("Pro CLI surface", "PASS", "Pricing, license, audit, and launch-pack commands are wired.")]


def _license_fulfillment(root: Path) -> list[LaunchCheck]:
    helper = root / "scripts" / "issue_license.py"
    text = _read_text(helper)
    if not helper.is_file():
        return [LaunchCheck("License fulfillment", "FAIL", "scripts/issue_license.py is missing.")]
    if "_license_checksum" not in text:
        return [LaunchCheck("License fulfillment", "FAIL", "License issuer does not use the runtime checksum format.")]
    return [LaunchCheck("License fulfillment", "PASS", "Manual license issuing helper is present.")]


def _test_coverage(root: Path) -> list[LaunchCheck]:
    tests = list((root / "tests").glob("test_*.py")) if (root / "tests").is_dir() else []
    if len(tests) < 6:
        return [LaunchCheck("Tests", "FAIL", f"Only {len(tests)} test files were found.")]
    return [LaunchCheck("Tests", "PASS", f"{len(tests)} test files were found.")]


def _ci_configuration(root: Path) -> list[LaunchCheck]:
    workflow_root = root / ".github" / "workflows"
    workflows = list(workflow_root.glob("*.yml")) + list(workflow_root.glob("*.yaml")) if workflow_root.is_dir() else []
    if not workflows:
        return [LaunchCheck("CI", "WARN", "No GitHub Actions workflow was found.")]
    return [LaunchCheck("CI", "PASS", "GitHub Actions workflow is present.")]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


if __name__ == "__main__":
    main()
