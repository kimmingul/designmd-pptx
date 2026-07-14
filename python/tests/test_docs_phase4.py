"""Structural docs/templates checks for Phase 4 (#38/#41/#43)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class DocsPhase4(unittest.TestCase):
    def test_required_docs_exist_with_sections(self) -> None:
        required = {
            "docs/index.md": ["Quick start", "Guides"],
            "docs/install.md": ["doctor --install", "pip"],
            "docs/concepts.md": ["Backends", "Quality gates"],
            "docs/commands.md": ["a11y", "benchmark", "doctor"],
            "docs/gallery.md": ["Scaffold", "Accessibility"],
            "docs/migration-v1-v2.md": ["Breaking", "Suggested upgrade"],
            "docs/maturity-roadmap.md": ["v2.0", "v2.1", "v3.0"],
            "docs/production-readiness.md": ["Threshold", "a11y", "Fixture benchmark"],
            "docs/governance.md": ["Label", "PR merge", "Triage"],
            "CONTRIBUTING.md": ["Dev setup", "Pattern", "PR checks", "Governance"],
        }
        for rel, needles in required.items():
            path = ROOT / rel
            self.assertTrue(path.is_file(), f"missing {rel}")
            text = path.read_text(encoding="utf-8")
            self.assertGreater(len(text.strip()), 200, f"{rel} too short / stub")
            for n in needles:
                self.assertIn(n, text, f"{rel} missing section marker {n!r}")

    def test_issue_templates_exist(self) -> None:
        for rel in (
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/feedback.md",
            ".github/ISSUE_TEMPLATE/config.yml",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_ci_has_benchmark_job(self) -> None:
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("benchmark", ci)
        self.assertIn("designmd_pptx benchmark", ci)
        self.assertIn("designmd_pptx a11y", ci)


if __name__ == "__main__":
    unittest.main()
