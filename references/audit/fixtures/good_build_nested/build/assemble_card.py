#!/usr/bin/env python3
import json, sys
from pathlib import Path
base = Path(__file__).resolve().parents[1]
card_path = base / 'good_build_nested.json'
entries_path = base / 'build' / 'all_entries.json'
out = Path(sys.argv[1]) if len(sys.argv) > 1 else base / 'good_build_nested.json'
card = json.loads(card_path.read_text(encoding='utf-8'))
entries = json.loads(entries_path.read_text(encoding='utf-8'))
card['data']['character_book']['entries'] = entries
card['data']['name'] = card['name']
out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)
