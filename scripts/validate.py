#!/usr/bin/env python3
"""Run the repository's offline validation suite; no provider network calls."""

from __future__ import annotations

import compileall
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from biomedical_manuscript.validation import validate_registry, validate_skill_files  # noqa: E402


def main() -> int:
    errors = validate_skill_files(ROOT) + validate_registry(ROOT)
    if errors:
        print("Repository contract validation failed:")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print("PASS: skill metadata and required workflow contracts")
    print("PASS: versioned guideline registry structure")
    if not compileall.compile_dir(str(ROOT / "src"), quiet=1):
        print("FAIL: Python compile check")
        return 1
    print("PASS: Python compile check")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    print(f"PASS: {result.testsRun} offline unit/integration/adversarial checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
