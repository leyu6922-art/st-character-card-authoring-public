#!/usr/bin/env python3
"""Source-tree shim for the sanitized Public Core integrity auditor.

The public exporter replaces this path with the reviewed neutral implementation
from release/public-core/audit_public_core_integrity.py.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "release" / "public-core" / "audit_public_core_integrity.py"

if __name__ == "__main__":
    if "--skill-root" not in sys.argv:
        sys.argv.extend(["--skill-root", str(REPO_ROOT)])
    runpy.run_path(str(TARGET), run_name="__main__")
