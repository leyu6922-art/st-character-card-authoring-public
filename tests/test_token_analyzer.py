from __future__ import annotations

import json


def test_token_analyzer_uses_shared_matcher_and_never_mutates(load_script_module, tmp_path):
    analyzer = load_script_module("analyze_token_load.py")
    card_path = tmp_path / "card.json"
    card = {
        "data": {
            "first_mes": "primary only",
            "character_book": {
                "entries": [
                    {
                        "id": 9,
                        "comment": "requires secondary",
                        "content": "body",
                        "keys": ["primary"],
                        "secondary_keys": ["secondary"],
                        "constant": False,
                        "enabled": True,
                        "selective": True,
                        "extensions": {},
                    }
                ]
            },
        }
    }
    card_path.write_text(json.dumps(card), encoding="utf-8")
    original = card_path.read_bytes()

    report = analyzer.analyze_token_load(card_path)

    assert report["triggered_entries"] == 0
    assert card_path.read_bytes() == original
