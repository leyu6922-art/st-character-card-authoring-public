from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ARCH_ROOT = ROOT.parents[1] / "software-development" / "st-card-architecture-patterns" / "references"


pytestmark = pytest.mark.skipif(
    not ARCH_ROOT.exists(),
    reason="optional sibling skill st-card-architecture-patterns is not available",
)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_legacy_route_marker_references_cannot_be_mistaken_for_native_contracts():
    docs = [
        ROOT / "references" / "design-patterns" / "no-variable-route-marker-audit.md",
        ROOT / "references" / "workflows" / "progressive-card-versioned-repair.md",
        ROOT / "references" / "design-patterns" / "material-pack-entry-pattern.md",
        ARCH_ROOT / "stage-driven-greeting-card.md",
    ]
    for doc in docs:
        body = text(doc)
        assert "历史" in body or "legacy" in body.lower(), doc
        assert "native" in body.lower(), doc


def test_phase_memory_template_separates_native_and_external_route_sources():
    body = text(ARCH_ROOT / "phase-memory-gate-architecture.md")
    assert "native Greeting-title" in body
    assert "外部 Author's Note" in body
    assert "不得直接复制" in body
