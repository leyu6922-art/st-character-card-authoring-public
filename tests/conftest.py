from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def skill_root() -> Path:
    return SKILL_ROOT


@pytest.fixture
def load_script_module():
    def _load(filename: str):
        path = SCRIPTS_DIR / filename
        module_name = f"test_{path.stem}_{id(path)}"
        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            assert spec and spec.loader, f"cannot load {path}"
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        finally:
            if sys.path and sys.path[0] == str(SCRIPTS_DIR):
                sys.path.pop(0)

    return _load
