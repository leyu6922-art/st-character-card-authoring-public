# Unicode Encoding Pitfalls for Character Cards

## Pitfall: `\uXXXX` escape sequences stored as literal text

### Symptom
SillyTavern displays `\u2764` instead of ❤, or `\U0001f4cd` instead of 📍, in opening scenes or entry content.

### Root Cause
When using `write_file` to create text files (e.g., opening scene drafts), Python unicode escape sequences like `\u2764` are written as **6 literal characters** (`\`, `u`, `2`, `7`, `6`, `4`), NOT as the actual ❤ character. When these text files are later read and embedded into the JSON card, the literal escape sequences persist.

In contrast, when using `execute_code` with `json.dump()`, Python interprets `\u2764` in source code strings as the actual character ❤, and `json.dump` serializes it correctly.

### The Problematic Pattern
```python
# ❌ WRONG: write_file writes literal \u2764 as 6 chars
write_file("/tmp/scene.txt", "没事~\u2764 妈妈说")  # File contains: 没事~\u2764 妈妈说

# Then in execute_code:
with open("/tmp/scene.txt", "r") as f:
    text = f.read()  # text contains literal \u2764, NOT ❤
```

### The Fix
```python
# ✅ CORRECT: Use actual unicode character in execute_code
content = "没事~\u2764 妈妈说"  # Python interprets \u2764 as ❤
# content now contains the actual heart character

# OR: use the actual character directly
content = "没事~❤ 妈妈说"
```

### Verification
After building the JSON card, check for literal escape sequences in the raw file:
```python
import re
with open("card.json", "r") as f:
    raw = f.read()
literal_u = re.findall(r'(?<!\\)\\u[0-9a-fA-F]{4}', raw)
literal_U = re.findall(r'(?<!\\)\\U[0-9a-fA-F]{8}', raw)
# Both should be 0
```

### If the JSON is already corrupted
If literal escapes are already in the JSON file, **do NOT do raw string replacement on the JSON file** — this will corrupt the JSON structure (see T13 in pitfall-library.md).

Instead, load the JSON, fix the content, and re-save:
```python
import json, re

def fix_escapes(text):
    def repl(m):
        try: return chr(int(m.group(1), 16))
        except: return m.group(0)
    return re.sub(r'\\u([0-9a-fA-F]{4})', repl, text)

with open("card.json", "r", encoding="utf-8") as f:
    card = json.load(f)

# Fix all string fields
card["data"]["first_mes"] = fix_escapes(card["data"]["first_mes"])
for e in card["data"]["character_book"]["entries"]:
    e["content"] = fix_escapes(e["content"])

with open("card.json", "w", encoding="utf-8") as f:
    json.dump(card, f, ensure_ascii=False, indent=2)
```

If the JSON is so corrupted it can't be loaded, rebuild from scratch using the /tmp/ part files and text files.

## Pitfall: Emoji in Supplementary Unicode Planes

### Symptom
SillyTavern displays garbled text or raw codes for emoji like 📍🕐👥🔥.

### Root Cause
Emoji characters live in Unicode supplementary planes (U+1F000+). Some SillyTavern configurations or JSON parsers don't handle these correctly.

### The Fix
Replace all supplementary-plane emoji with text labels:
- 📍 → [地点]
- 🕐 → [时间]
- 👥 → [人员]
- 🔥 → [状态]
- ⚠️ → [注意]

Characters in the BMP (U+0000–U+FFFF) are generally safe:
- ❤ (U+2764) — OK
- → (U+2192) — OK
- ═ ║ ╔ ╗ ╚ ╝ (box drawing) — OK

### Detection
```python
for i, ch in enumerate(text):
    if ord(ch) > 0xFFFF:
        print(f"pos {i}: U+{ord(ch):04X} {repr(ch)}")
```

### Universal Fix: Replace ALL Supplementary Plane Characters
When fixing old cards that may contain unknown emoji, don't rely on a fixed map — use a universal scan that replaces **all** U+1F000+ characters:

```python
def replace_all_emoji(text):
    """Replace all supplementary plane characters (U+1F000+) with text labels."""
    result = []
    for ch in text:
        code = ord(ch)
        if code > 0xFFFF:
            result.append(f'[U+{code:04X}]')
        else:
            result.append(ch)
    return ''.join(result)

# Apply to all text fields in the card
for e in card['data']['character_book']['entries']:
    e['content'] = replace_all_emoji(e['content'])
card['data']['first_mes'] = replace_all_emoji(card['data']['first_mes'])
for i, a in enumerate(card['data'].get('alternate_greetings', [])):
    card['data']['alternate_greetings'][i] = replace_all_emoji(a)
```

This catches any emoji (💧👦👗🎭📋🗓 etc.) without needing to maintain a map. The `[U+XXXX]` labels are readable and won't cause rendering issues.
