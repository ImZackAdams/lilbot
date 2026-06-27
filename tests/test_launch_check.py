from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.launch_check import exit_code, render_report, run_checks


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LaunchCheckTests(unittest.TestCase):
    def test_launch_check_passes_without_failures_for_repo(self) -> None:
        checks = run_checks(PROJECT_ROOT)
        report = render_report(checks)

        self.assertEqual(exit_code(checks), 0)
        self.assertIn("Lilbot Pro launch check", report)
        self.assertIn("[PASS] Required files", report)
        self.assertIn("[WARN] Checkout configuration", report)

    def test_launch_check_fails_for_missing_product_files(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            checks = run_checks(Path(tempdir))

        self.assertEqual(exit_code(checks), 1)
        self.assertTrue(any(check.status == "FAIL" for check in checks))
