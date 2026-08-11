#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parent
card_path = root / 'bad_build_unsynced.json'
out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / '_rebuilt.json'
card = json.loads(card_path.read_text(encoding='utf-8'))
entries = json.loads((root / 'build' / 'all_entries.json').read_text(encoding='utf-8'))
card['data']['character_book']['entries'] = entries
out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)
