from __future__ import annotations


def test_source_material_coverage_counts_entries_with_canonical_excerpt(load_script_module):
    checker = load_script_module("audit_source_material_coverage.py")
    card = {
        "data": {
            "character_book": {
                "entries": [
                    {
                        "id": 1,
                        "comment": "角色档案",
                        "content": "她把银杯放回桌面，窗外的雨声压住了脚步声，随后抬眼看向来人。",
                        "enabled": True,
                        "constant": False,
                        "extensions": {"entry_role": "common_content"},
                    },
                    {
                        "id": 2,
                        "comment": "场景资料",
                        "content": "这是没有来源摘录的原创补充材料。",
                        "enabled": True,
                        "constant": False,
                        "extensions": {"entry_role": "common_content"},
                    },
                    {
                        "id": 3,
                        "comment": "OOC系统常驻",
                        "content": "系统指令不计入原文素材覆盖率。",
                        "enabled": True,
                        "constant": True,
                        "extensions": {"entry_role": "system_constant"},
                    },
                ]
            }
        }
    }
    source = "前文无关。她把银杯放回桌面，窗外的雨声压住了脚步声，随后抬眼看向来人。后文无关。"

    result = checker.audit_card_data(card, source, min_quote_chars=16)

    assert result["eligible"] == 2
    assert result["matched"] == 1
    assert result["coverage"] == 0.5
    assert result["unmatched_ids"] == [2]
