from __future__ import annotations

import json


def write_card(tmp_path, content: str):
    card = tmp_path / "card.json"
    card.write_text(
        json.dumps(
            {
                "data": {
                    "character_book": {
                        "entries": [
                            {
                                "id": 1,
                                "comment": "可运行行为",
                                "content": content,
                                "enabled": True,
                                "constant": False,
                                "keys": ["角色"],
                                "secondary_keys": [],
                            }
                        ]
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    source = tmp_path / "source.txt"
    source.write_text("canonical source text that does not occur in the card", encoding="utf-8")
    return card, source


def test_legacy_source_coverage_keeps_default_minimum(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card, source = write_card(tmp_path, "framework-only anchor")

    result = gate.run_source_material_coverage(card, [source])

    assert result.status == "FAIL"
    assert any("CANONICAL_SOURCE_COVERAGE_LOW" in message for message in result.errors)


def test_curated_anchor_source_coverage_is_diagnostic_without_explicit_minimum(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card, source = write_card(tmp_path, "framework-only anchor")

    result = gate.run_source_material_coverage(
        card,
        [source],
        minimum=None,
        corpus_mode="curated_anchor_set",
    )

    assert result.status == "PASS"
    assert result.errors == []
    assert any("curated_anchor_set" in note for note in result.notes)
