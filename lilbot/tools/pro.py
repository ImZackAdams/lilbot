"""Paid repository productization tools."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from lilbot.config import LilbotConfig
from lilbot.licensing import load_license_status, render_upgrade_required
from lilbot.tools.base import Tool
from lilbot.tools.filesystem import iter_workspace_files, is_probably_text, read_text_preview
from lilbot.utils.formatting import truncate_text


PACKAGE_FILES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "Cargo.toml",
    "go.mod",
}
README_FILES = {"README", "README.md", "README.rst"}
LICENSE_FILES = {"LICENSE", "LICENSE.md", "COPYING"}
CHANGELOG_FILES = {"CHANGELOG.md", "CHANGELOG", "HISTORY.md"}
ENV_SAMPLE_FILES = {".env.example", ".env.sample", "example.env"}
CHECKOUT_TERMS = (
    "stripe",
    "gumroad",
    "paddle",
    "lemonsqueezy",
    "checkout",
    "pricing",
    "subscription",
    "license activate",
    "license_key",
    "license key",
)
IGNORED_AUDIT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".onnx"}


@dataclass(frozen=True)
class AuditSignal:
    name: str
    status: str
    detail: str
    recommendation: str

    @property
    def points(self) -> int:
        if self.status == "PASS":
            return 2
        if self.status == "WARN":
            return 1
        return 0


class ProductReadinessAuditTool(Tool):
    name = "product_readiness_audit"
    description = "Audit a repository for launch, monetization, packaging, and support readiness. Lilbot Pro required."
    args_schema = {"path": "Workspace-relative repository path. Defaults to '.'."}

    def execute(self, **kwargs: object) -> str:
        status = load_license_status()
        if not status.active:
            return render_upgrade_required("Product readiness audit", status)

        path = str(kwargs.get("path", ".")).strip() or "."
        return render_product_readiness_audit(self.config, path)


def render_product_readiness_audit(config: LilbotConfig, path: str = ".") -> str:
    """Render a deterministic business-readiness audit for a workspace repository."""

    try:
        root = config.resolve_workspace_path(path, must_exist=True)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not root.is_dir():
        return f"Not a directory: {config.display_path(root)}"

    files = [
        file
        for file in iter_workspace_files(config, root, limit=config.repo_file_limit)
        if file.suffix.lower() not in IGNORED_AUDIT_SUFFIXES
    ]
    relative_files = {file.relative_to(root).as_posix(): file for file in files}
    names = {file.name for file in files}
    lower_paths = {relative.lower() for relative in relative_files}
    text_index = _build_text_index(files, root, config)

    signals = [
        _positioning_signal(relative_files, names),
        _packaging_signal(names),
        _onboarding_signal(names, text_index),
        _test_signal(lower_paths),
        _release_signal(lower_paths, names),
        _monetization_signal(relative_files, text_index),
        _license_signal(names),
        _support_signal(lower_paths, names),
        _config_hygiene_signal(names),
        _safety_signal(lower_paths, text_index),
    ]
    score = _score(signals)
    extension_counter = Counter(file.suffix.lower() or "<no extension>" for file in files)
    license_status = load_license_status()

    lines = [
        f"Lilbot Pro product readiness audit for {config.display_path(root)}:",
        f"- tier: {license_status.tier_label}",
        f"- score: {score}/100",
        f"- scanned_files: {len(files)}",
        f"- top_extensions: {_format_counter(extension_counter, 6)}",
        "",
        "Findings",
    ]
    for signal in signals:
        lines.append(f"[{signal.status}] {signal.name}: {signal.detail}")
        lines.append(f"  Next: {signal.recommendation}")

    blockers = [signal for signal in signals if signal.status == "FAIL"]
    warnings = [signal for signal in signals if signal.status == "WARN"]
    lines.append("")
    lines.append("Launch priorities")
    if blockers:
        for index, signal in enumerate(blockers[:4], start=1):
            lines.append(f"{index}. {signal.name}: {signal.recommendation}")
    elif warnings:
        for index, signal in enumerate(warnings[:4], start=1):
            lines.append(f"{index}. {signal.name}: {signal.recommendation}")
    else:
        lines.append("1. Ship the current paid workflow, then measure conversion from `lilbot pricing` to activation.")

    lines.append("")
    lines.append("Revenue path")
    lines.append("1. Create a Stripe Payment Link, Gumroad product, or billing page for Lilbot Pro.")
    lines.append("2. Set LILBOT_CHECKOUT_URL to that purchase URL in release, docs, or support scripts.")
    lines.append("3. Deliver license keys after purchase and ask customers to run `lilbot license activate <key>`.")
    return "\n".join(lines)


def _build_text_index(files: list[Path], root: Path, config: LilbotConfig) -> dict[str, str]:
    indexed: dict[str, str] = {}
    for file in files[: config.repo_file_limit]:
        if len(indexed) >= 120:
            break
        if not is_probably_text(file):
            continue
        try:
            text = read_text_preview(file, min(config.file_preview_chars, 8000))
        except OSError:
            continue
        indexed[file.relative_to(root).as_posix()] = text.lower()
    return indexed


def _positioning_signal(relative_files: dict[str, Path], names: set[str]) -> AuditSignal:
    readme_name = next((name for name in README_FILES if name in names), None)
    if not readme_name:
        return AuditSignal(
            "Positioning",
            "FAIL",
            "No README was found.",
            "Add a README that names the buyer, the painful job, and the first command to run.",
        )

    try:
        text = relative_files[readme_name].read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    if len(text.strip()) >= 800 and any(term in text.lower() for term in ("quick start", "install", "pricing", "pro")):
        return AuditSignal(
            "Positioning",
            "PASS",
            f"{readme_name} has buyer-facing setup and product copy.",
            "Keep the top of the README focused on the paid job-to-be-done and conversion command.",
        )
    return AuditSignal(
        "Positioning",
        "WARN",
        f"{readme_name} exists, but the product promise or purchase path is thin.",
        "Open with who buys this, what result they get, and how to purchase Pro.",
    )


def _packaging_signal(names: set[str]) -> AuditSignal:
    found = sorted(names.intersection(PACKAGE_FILES))
    if found:
        return AuditSignal(
            "Packaging",
            "PASS",
            f"Package metadata found in {', '.join(found[:3])}.",
            "Use the package metadata as the source of truth for releases and store listing copy.",
        )
    return AuditSignal(
        "Packaging",
        "FAIL",
        "No common package manifest was found.",
        "Add a package manifest so buyers can install and update the product predictably.",
    )


def _onboarding_signal(names: set[str], text_index: dict[str, str]) -> AuditSignal:
    combined = "\n".join(text_index.values())
    has_env_sample = bool(names.intersection(ENV_SAMPLE_FILES))
    has_doctor = "doctor" in combined or "self-test" in combined
    if has_env_sample and has_doctor:
        return AuditSignal(
            "Onboarding",
            "PASS",
            "Setup diagnostics and sample environment configuration are documented.",
            "Keep first-run setup under five minutes for the default buyer machine.",
        )
    if has_env_sample or has_doctor:
        return AuditSignal(
            "Onboarding",
            "WARN",
            "Some onboarding assets exist, but first-run recovery is incomplete.",
            "Document both configuration examples and a one-command health check.",
        )
    return AuditSignal(
        "Onboarding",
        "FAIL",
        "No setup diagnostics or environment template were detected.",
        "Add a first-run command, a doctor command, and a sample environment file.",
    )


def _test_signal(lower_paths: set[str]) -> AuditSignal:
    test_paths = [path for path in lower_paths if path.startswith("tests/") or "/test_" in path or path.endswith("_test.py")]
    if len(test_paths) >= 4:
        return AuditSignal(
            "Tests",
            "PASS",
            f"{len(test_paths)} test-related files were found.",
            "Add paid-flow regression tests before each new Pro workflow ships.",
        )
    if test_paths:
        return AuditSignal(
            "Tests",
            "WARN",
            f"{len(test_paths)} test-related file(s) were found.",
            "Add tests for install, activation, upgrade prompts, and paid commands.",
        )
    return AuditSignal(
        "Tests",
        "FAIL",
        "No tests were detected.",
        "Add a focused test suite before charging customers.",
    )


def _release_signal(lower_paths: set[str], names: set[str]) -> AuditSignal:
    has_ci = any(path.startswith(".github/workflows/") for path in lower_paths) or ".gitlab-ci.yml" in lower_paths
    has_release_asset = bool(names.intersection({"Dockerfile", "Makefile", "CHANGELOG.md", "CHANGELOG"}))
    if has_ci and has_release_asset:
        return AuditSignal(
            "Release",
            "PASS",
            "CI and release-support files are present.",
            "Publish a repeatable release checklist that includes license activation testing.",
        )
    if has_ci or has_release_asset:
        return AuditSignal(
            "Release",
            "WARN",
            "Some release assets exist, but the release path is not fully automated.",
            "Add CI plus a changelog or release script so paid customers get predictable updates.",
        )
    return AuditSignal(
        "Release",
        "FAIL",
        "No CI or release-support files were detected.",
        "Add a minimal CI workflow and release checklist before the first paid launch.",
    )


def _monetization_signal(relative_files: dict[str, Path], text_index: dict[str, str]) -> AuditSignal:
    matches: list[str] = []
    for relative, text in text_index.items():
        if any(term in text for term in CHECKOUT_TERMS):
            matches.append(relative)

    billing_files = [
        relative
        for relative in relative_files
        if any(term in relative.lower() for term in ("pricing", "billing", "license", "checkout", "stripe"))
    ]
    combined = sorted(set(matches + billing_files))
    if combined:
        return AuditSignal(
            "Monetization",
            "PASS",
            f"Payment or licensing signals found in {truncate_text(', '.join(combined[:4]), 180)}.",
            "Connect the checkout URL to the live payment provider and document fulfillment.",
        )
    return AuditSignal(
        "Monetization",
        "FAIL",
        "No pricing, checkout, billing, or licensing surface was detected.",
        "Add pricing copy, a checkout URL, license activation, and a paid command that proves value.",
    )


def _license_signal(names: set[str]) -> AuditSignal:
    if names.intersection(LICENSE_FILES):
        return AuditSignal(
            "Legal",
            "PASS",
            "A project license file is present.",
            "For Pro sales, add customer terms that cover support, refunds, and paid entitlement limits.",
        )
    return AuditSignal(
        "Legal",
        "WARN",
        "No project license file was detected.",
        "Add a license file and customer-facing paid terms before broad distribution.",
    )


def _support_signal(lower_paths: set[str], names: set[str]) -> AuditSignal:
    has_support = "support.md" in lower_paths or ".github/issue_template" in lower_paths
    has_docs = any(path.startswith("docs/") for path in lower_paths)
    if has_support or has_docs or "ROADMAP.md" in names:
        return AuditSignal(
            "Support",
            "PASS",
            "Support, docs, or roadmap assets are present.",
            "Add a Pro support promise and response-time expectation near checkout.",
        )
    return AuditSignal(
        "Support",
        "WARN",
        "No support docs, issue templates, or roadmap were detected.",
        "Add a lightweight support channel and refund policy before paid promotion.",
    )


def _config_hygiene_signal(names: set[str]) -> AuditSignal:
    if ".env" in names:
        return AuditSignal(
            "Config hygiene",
            "WARN",
            "A .env file is present in the repository scan.",
            "Keep only .env.example in source control and move real customer or billing secrets out of the repo.",
        )
    if names.intersection(ENV_SAMPLE_FILES):
        return AuditSignal(
            "Config hygiene",
            "PASS",
            "Environment examples exist without a scanned .env file.",
            "Keep billing and license secrets documented as placeholders only.",
        )
    return AuditSignal(
        "Config hygiene",
        "WARN",
        "No environment template was detected.",
        "Add .env.example with safe placeholders for checkout and license settings.",
    )


def _safety_signal(lower_paths: set[str], text_index: dict[str, str]) -> AuditSignal:
    combined = "\n".join(text_index.values())
    has_policy = any("safety" in path or "shell_policy" in path for path in lower_paths)
    if has_policy and any(term in combined for term in ("blocked", "dangerous", "workspace root", "restricted")):
        return AuditSignal(
            "Safety",
            "PASS",
            "Safety policy and restricted execution language were detected.",
            "Put the safety model in sales copy because local automation buyers care about blast radius.",
        )
    if has_policy:
        return AuditSignal(
            "Safety",
            "WARN",
            "Safety-related files exist, but the buyer-facing safety story is thin.",
            "Document what the product can and cannot do to a customer's machine.",
        )
    return AuditSignal(
        "Safety",
        "WARN",
        "No explicit safety policy was detected.",
        "Add a safety model before marketing automation features.",
    )


def _score(signals: list[AuditSignal]) -> int:
    if not signals:
        return 0
    earned = sum(signal.points for signal in signals)
    return round((earned / (len(signals) * 2)) * 100)


def _format_counter(counter: Counter[str], limit: int) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{name} ({count})" for name, count in counter.most_common(limit))
