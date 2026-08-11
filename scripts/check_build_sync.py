#!/usr/bin/env python3
"""
Build/source sync gate for SillyTavern character cards.

Checks whether final card JSON is synchronized with file-first build sources
(build/all_entries.json and/or assemble_card.py). Static source comparison is the
safe default. Builder execution requires the explicit --execute-builder opt-in;
when enabled it runs only inside a temporary project copy with a reduced
environment. The gate is non-destructive and _gate_rebuild.json is kept only when
--keep-rebuild is explicitly requested.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER_ENV_ALLOWLIST = {
    "PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR",
    "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LANG", "LC_ALL",
    "PYTHONUTF8", "PYTHONIOENCODING",
}



def load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def load_card_entries(card_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    card = load_json(card_path)
    data = card.get('data', card)
    book = data.get('character_book') or card.get('character_book') or {}
    entries = book.get('entries', [])
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        raise ValueError('character_book.entries is not a list/dict')
    return card, data, entries


def load_all_entries_source(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
    """Load legacy entry lists or an explicit metadata-capable character_book source."""
    raw = load_json(path)
    if isinstance(raw, list):
        return raw, None
    if isinstance(raw, dict):
        book = raw.get("character_book")
        if isinstance(book, dict) and isinstance(book.get("entries"), list):
            return book["entries"], book
        if isinstance(raw.get("entries"), list):
            metadata_fields = {"name", "description", "scan_depth", "token_budget", "recursive_scanning", "extensions"}
            return raw["entries"], raw if metadata_fields.intersection(raw) else None
    raise ValueError('build/all_entries.json must be a list or contain entries[]')


def load_all_entries(path: Path) -> List[Dict[str, Any]]:
    """Backward-compatible entry-only view used by older callers."""
    entries, _metadata = load_all_entries_source(path)
    return entries


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


RUNTIME_ONLY_EXTENSION_FIELDS = {"display_index", "triggered"}
SEMANTIC_EXTENSION_DEFAULTS = {
    "position": 4,
    "exclude_recursion": False,
    "prevent_recursion": False,
    "selectiveLogic": 0,
    "useProbability": True,
    "probability": 100,
}
SEMANTIC_ENTRY_FIELDS = (
    "id", "keys", "secondary_keys", "comment", "content", "constant", "enabled",
    "selective", "selectiveLogic", "insertion_order", "position", "use_regex", "addMemo",
    "case_sensitive", "priority", "name",
)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    return value


def canonicalize_extensions(extensions: Any) -> Dict[str, Any]:
    raw = dict(extensions) if isinstance(extensions, dict) else {}
    for key in RUNTIME_ONLY_EXTENSION_FIELDS:
        raw.pop(key, None)
    for key, default in SEMANTIC_EXTENSION_DEFAULTS.items():
        if raw.get(key) is None:
            raw[key] = default
    return _canonical_value(raw)


def canonicalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    canonical: Dict[str, Any] = {}
    for field in SEMANTIC_ENTRY_FIELDS:
        value = entry.get(field)
        if field in {"keys", "secondary_keys"}:
            value = list(value or [])
        elif field in {"constant", "selective", "use_regex", "addMemo"}:
            value = bool(value)
        elif field == "enabled":
            value = True if value is None else bool(value)
        canonical[field] = _canonical_value(value)
    canonical["extensions"] = canonicalize_extensions(entry.get("extensions"))
    return canonical


def canonicalize_character_book(book: Any) -> Dict[str, Any]:
    """Compare Lorebook metadata without duplicating entry comparison."""
    raw = dict(book) if isinstance(book, dict) else {}
    fields = ("name", "description", "scan_depth", "token_budget", "recursive_scanning")
    canonical = {field: _canonical_value(raw.get(field)) for field in fields}
    canonical["extensions"] = _canonical_value(raw.get("extensions") or {})
    return canonical


def _diff_values(final: Any, build: Any, path: str) -> List[str]:
    if type(final) is not type(build):
        return [path]
    if isinstance(final, dict):
        diffs: List[str] = []
        for key in sorted(set(final) | set(build)):
            child_path = f"{path}.{key}" if path else key
            if key not in final or key not in build:
                diffs.append(child_path)
            else:
                diffs.extend(_diff_values(final[key], build[key], child_path))
        return diffs
    if isinstance(final, list):
        diffs = []
        if len(final) != len(build):
            diffs.append(f"{path}.length")
        for index, (left, right) in enumerate(zip(final, build)):
            diffs.extend(_diff_values(left, right, f"{path}[{index}]"))
        return diffs
    return [] if final == build else [path]


def _entry_drift_rule(path: str) -> str:
    first = re.split(r"[.\[]", path, maxsplit=1)[0]
    return {
        "keys": "BUILD_ENTRY_KEYS_DRIFT",
        "secondary_keys": "BUILD_ENTRY_SECONDARY_KEYS_DRIFT",
        "enabled": "BUILD_ENTRY_ENABLED_DRIFT",
        "constant": "BUILD_ENTRY_CONSTANT_DRIFT",
        "selective": "BUILD_ENTRY_SELECTIVE_DRIFT",
        "extensions": "BUILD_ENTRY_EXTENSIONS_DRIFT",
        "content": "BUILD_ENTRY_CONTENT_DRIFT",
    }.get(first, "BUILD_ENTRY_SEMANTIC_DRIFT")


def compare_entries(final_entries: Sequence[Dict[str, Any]], build_entries: Sequence[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    if len(final_entries) != len(build_entries):
        issues.append(f"[BUILD_ENTRY_COUNT_DRIFT] entries.length: final={len(final_entries)} build={len(build_entries)}")
    final_ids = [entry.get("id") for entry in final_entries]
    build_ids = [entry.get("id") for entry in build_entries]
    if final_ids != build_ids:
        issues.append(f"[BUILD_ENTRY_ID_ORDER_DRIFT] entries.id: final={final_ids[:8]!r} build={build_ids[:8]!r}")
    for index, (final_entry, build_entry) in enumerate(zip(final_entries, build_entries)):
        entry_id = final_entry.get("id", index)
        for path in _diff_values(canonicalize_entry(final_entry), canonicalize_entry(build_entry), ""):
            rule_id = _entry_drift_rule(path)
            issues.append(f"[{rule_id}] entries[{entry_id}].{path}: final/build semantic values differ")
    return issues


def canonicalize_card_fields(card: Dict[str, Any]) -> Dict[str, Any]:
    data = card.get("data", card)
    fields = (
        "name", "description", "personality", "scenario", "first_mes", "alternate_greetings",
        "mes_example", "creator", "character_version", "creator_notes", "system_prompt",
        "post_history_instructions", "group_only_greetings", "tags",
    )
    result = {field: _canonical_value(data.get(field)) for field in fields}
    result["character_book"] = canonicalize_character_book(data.get("character_book"))
    data_extensions = dict(data.get("extensions") or {})
    result["regex_scripts"] = _canonical_value(data_extensions.get("regex_scripts", []))
    return result


def compare_card_fields(final_card: Dict[str, Any], rebuild_card: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    final_data = final_card.get('data', final_card)
    rebuild_data = rebuild_card.get('data', rebuild_card)
    for field in ['spec', 'spec_version']:
        if final_card.get(field) != rebuild_card.get(field):
            issues.append(f'[BUILD_CARD_TOPLEVEL_DRIFT] {field}: final={final_card.get(field)!r} rebuild={rebuild_card.get(field)!r}')
        if final_data.get(field) != rebuild_data.get(field):
            issues.append(f'[BUILD_CARD_DATA_DRIFT] data.{field}: final={final_data.get(field)!r} rebuild={rebuild_data.get(field)!r}')
    for path in _diff_values(canonicalize_card_fields(final_card), canonicalize_card_fields(rebuild_card), "data"):
        issues.append(f'[BUILD_CARD_DATA_DRIFT] {path}: final/rebuild semantic values differ')
    return issues


def find_assemble_script(project_dir: Path) -> Path | None:
    for candidate in [
        project_dir / 'assemble_card.py',
        project_dir / 'build' / 'assemble_card.py',
        project_dir / 'build_data' / 'assemble_card.py',
    ]:
        if candidate.exists():
            return candidate
    return None


def script_has_absolute_path_risk(script: Path, original_project_dir: Path) -> str | None:
    text = script.read_text(encoding='utf-8', errors='ignore')
    if str(original_project_dir) in text or str(original_project_dir).replace('\\', '/') in text:
        return 'assemble脚本含原项目绝对路径，跳过执行以避免覆盖原卡'
    if re.search(r'[A-Za-z]:[\\/].{0,120}\.json', text) or re.search(r'/(?:mnt|c|d)/.{0,160}\.json', text):
        return 'assemble脚本疑似含绝对JSON输出路径，跳过执行以避免副作用'
    return None


def script_accepts_output_arg(script: Path) -> bool:
    text = script.read_text(encoding='utf-8', errors='ignore')
    return 'sys.argv' in text or 'argparse' in text


def snapshot_json_files(root: Path) -> Dict[Path, str]:
    snap: Dict[Path, str] = {}
    for p in root.rglob('*.json'):
        try:
            snap[p.relative_to(root)] = file_hash(p)
        except OSError:
            pass
    return snap


def discover_rebuild_json(temp_project: Path, before: Dict[Path, str], preferred_out: Path, stdout_stderr: str, final_rel: Path) -> Path | None:
    if preferred_out.exists():
        return preferred_out
    # stdout path discovery
    for token in stdout_stderr.replace('\n', ' ').split():
        raw = token.strip('"\'`，,')
        if not raw.lower().endswith('.json'):
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = temp_project / p
        if p.exists():
            return p
    # common case: script ignored argv and rewrote the final card path in temp copy
    final_candidate = temp_project / final_rel
    if final_candidate.exists() and before.get(final_rel) != file_hash(final_candidate):
        return final_candidate
    after = snapshot_json_files(temp_project)
    changed = [rel for rel, h in after.items() if before.get(rel) != h]
    if changed:
        # Prefer non-report card-looking files, fall back to first changed json.
        changed_sorted = sorted(changed, key=lambda r: (('report' in r.name.lower()) or ('summary' in r.name.lower()), len(str(r))))
        return temp_project / changed_sorted[0]
    return None


def run_validate(card_path: Path, greeting_mode: str = 'player_prose') -> Tuple[bool, List[str], List[str]]:
    validator = SCRIPT_DIR / 'validate_card.py'
    if not validator.exists():
        return True, [], ['validate_card.py not found; skipped']
    spec = importlib.util.spec_from_file_location('validate_card', validator)
    if spec is None or spec.loader is None:
        return False, ['cannot import validate_card.py'], []
    mod = importlib.util.module_from_spec(spec)
    sys.modules['validate_card'] = mod
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if sys.path and sys.path[0] == str(SCRIPT_DIR):
            sys.path.pop(0)
    return mod.validate_card(str(card_path), greeting_mode=greeting_mode)


def run_assemble_in_temp(
    project_dir: Path,
    card_path: Path,
    assemble_script: Path,
    keep_rebuild: bool = False,
    timeout: int = 60,
    greeting_mode: str = 'player_prose',
    execute_builder: bool = False,
    reproducibility_required: bool = False,
) -> Tuple[str, List[str], List[str], Path | None]:
    """Run a trusted builder in a temporary copy, or report static-only mode."""
    issues: List[str] = []
    notes: List[str] = []
    if not execute_builder:
        marker = 'DECLARED_UNVERIFIED' if reproducibility_required else 'STATIC_ONLY'
        requirement = 'reproducible build required by manifest; ' if reproducibility_required else ''
        return 'WARN', [], [
            f'{marker}: {requirement}build source statically checked; reproducible build NOT_VERIFIED; '
            'project builder execution not enabled',
        ], None
    risk = script_has_absolute_path_risk(assemble_script, project_dir)
    if risk:
        return 'WARN', [], [risk + '；仅完成all_entries静态比对，未验证assemble'], None

    with tempfile.TemporaryDirectory(prefix='st_gate_project_') as td:
        tmp_root = Path(td) / 'project'
        ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '*_delivery_gate_report.md', '*_worldbook_trigger_audit.md', '_gate_rebuild.json')
        shutil.copytree(project_dir, tmp_root, ignore=ignore)
        rel_script = assemble_script.relative_to(project_dir)
        temp_script = tmp_root / rel_script
        final_rel = card_path.relative_to(project_dir) if card_path.is_relative_to(project_dir) else Path(card_path.name)
        preferred_out = tmp_root / '_gate_rebuild.json'
        before = snapshot_json_files(tmp_root)
        cmd = [sys.executable, str(temp_script)]
        if script_accepts_output_arg(assemble_script):
            cmd.append(str(preferred_out))
        child_env = {key: value for key, value in os.environ.items() if key in BUILDER_ENV_ALLOWLIST}
        # Never inherit API keys, tokens, proxy credentials, or unrelated CLI env.
        # Pin both sides of the pipe to UTF-8 on Chinese Windows.
        child_env['PYTHONUTF8'] = '1'
        child_env['PYTHONIOENCODING'] = 'utf-8'
        try:
            proc = subprocess.run(
                cmd, cwd=str(tmp_root), text=True, encoding='utf-8', errors='replace',
                capture_output=True, stdin=subprocess.DEVNULL, timeout=timeout, env=child_env,
            )
        except subprocess.TimeoutExpired:
            return 'FAIL', [f'assemble脚本在临时目录运行超时（>{timeout}s）'], notes, None
        combined = (proc.stdout or '') + (proc.stderr or '')
        if proc.returncode != 0:
            return 'FAIL', [f'assemble脚本在临时目录运行失败 exit={proc.returncode}: {combined[-800:]}'], notes, None
        rebuild_path = discover_rebuild_json(tmp_root, before, preferred_out, combined, final_rel)
        if rebuild_path is None:
            return 'WARN', [], ['assemble脚本运行成功，但未发现新增/变更JSON；仅完成all_entries静态比对，未验证重组结果'], None
        final_card, _fd, final_entries = load_card_entries(card_path)
        rebuild_card, _rd, rebuild_entries = load_card_entries(rebuild_path)
        rebuild_issues = compare_entries(final_entries, rebuild_entries)
        rebuild_issues.extend(compare_card_fields(final_card, rebuild_card))
        if rebuild_issues:
            issues.extend(f'assemble重组不同步: {i}' for i in rebuild_issues)
        ok, v_errors, v_warnings = run_validate(rebuild_path, greeting_mode=greeting_mode)
        if not ok:
            issues.append('临时重组卡 validate_card.py 未通过: ' + '; '.join(v_errors[:5]))
        else:
            notes.append(f'临时目录assemble验证通过（warnings={len(v_warnings)}；未污染原项目）')
            if reproducibility_required:
                notes.append('INTEGRATION_VERIFIED: manifest-required reproducible builder executed with explicit external authorization')
        kept_path: Path | None = None
        if keep_rebuild:
            kept_path = project_dir / '_gate_rebuild.json'
            kept_path.write_text(rebuild_path.read_text(encoding='utf-8'), encoding='utf-8')
            notes.append(f'按 --keep-rebuild 保存临时重组卡: {kept_path}')
        return ('FAIL' if issues else 'PASS'), issues, notes, kept_path


def make_report(card_path: Path, project_dir: Path, status: str, issues: List[str], warnings: List[str], notes: List[str]) -> str:
    lines = [
        f'# Build Sync Gate — {card_path.name}',
        '',
        f'- card: `{card_path}`',
        f'- project_dir: `{project_dir}`',
        f'- status: **{status}**',
        '',
    ]
    if issues:
        lines.append('## Errors')
        lines.extend(f'- {i}' for i in issues)
        lines.append('')
    if warnings:
        lines.append('## Warnings')
        lines.extend(f'- {w}' for w in warnings)
        lines.append('')
    if notes:
        lines.append('## Notes')
        lines.extend(f'- {n}' for n in notes)
        lines.append('')
    return '\n'.join(lines)


def check_build_sync(
    card_path: Path,
    project_dir: Path,
    require_build: bool = False,
    keep_rebuild: bool = False,
    greeting_mode: str = 'player_prose',
    execute_builder: bool = False,
    reproducibility_required: bool = False,
) -> Tuple[str, List[str], List[str]]:
    """Return (status, issues, notes). status is PASS/WARN/FAIL/N/A."""
    issues: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []
    all_entries_path = project_dir / 'build' / 'all_entries.json'
    assemble_script = find_assemble_script(project_dir)
    has_all_entries = all_entries_path.exists()
    has_assemble = assemble_script is not None

    if not has_all_entries and not has_assemble:
        msg = '未检测到 build/all_entries.json、assemble_card.py、build/assemble_card.py 或 build_data/assemble_card.py'
        if require_build:
            return 'FAIL', [msg + '；项目声明file-first，必须补齐构建链路'], notes
        return 'N/A', [], [msg + '；build sync: N/A']

    final_card, final_data, final_entries = load_card_entries(card_path)

    if has_all_entries:
        build_entries, build_book = load_all_entries_source(all_entries_path)
        entry_issues = compare_entries(final_entries, build_entries)
        if entry_issues:
            issues.extend(f'all_entries不同步: {i}' for i in entry_issues)
        else:
            notes.append('build/all_entries.json 与最终JSON entries一致')
        if build_book is not None:
            final_book = final_data.get("character_book") or final_card.get("character_book") or {}
            for path in _diff_values(
                canonicalize_character_book(final_book),
                canonicalize_character_book(build_book),
                "character_book",
            ):
                issues.append(f'[BUILD_LOREBOOK_METADATA_DRIFT] {path}: final/build semantic values differ')
        else:
            warnings.append('build/all_entries.json 是纯 entries 源，无法比较 character_book metadata；使用 character_book 包装对象或 assemble 校验以覆盖元数据')
    else:
        warnings.append('未检测到 build/all_entries.json，无法静态比对源entries')

    if has_assemble and assemble_script is not None:
        status, asm_issues, asm_notes, rebuild_path = run_assemble_in_temp(
            project_dir,
            card_path,
            assemble_script,
            keep_rebuild=keep_rebuild,
            greeting_mode=greeting_mode,
            execute_builder=execute_builder,
            reproducibility_required=reproducibility_required,
        )
        if status == 'FAIL':
            issues.extend(f'assemble验证失败: {i}' for i in asm_issues)
        elif status == 'WARN':
            warnings.extend(asm_notes)
        else:
            notes.extend(asm_notes)
    else:
        warnings.append('未检测到 assemble_card.py / build/assemble_card.py / build_data/assemble_card.py；仅验证all_entries，未验证可复现assemble')

    if issues:
        return 'FAIL', issues, notes + [f'WARN: {w}' for w in warnings]
    if warnings:
        return 'WARN', [], notes + [f'WARN: {w}' for w in warnings]
    return 'PASS', [], notes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check file-first build sources are synchronized with final card JSON')
    parser.add_argument('card', help='final card JSON path')
    parser.add_argument('--project-dir', help='project dir containing build/all_entries.json and/or assemble_card.py/build/assemble_card.py/build_data/assemble_card.py; default: card parent')
    parser.add_argument('--require-build', action='store_true', help='treat missing build chain as failure')
    parser.add_argument('--execute-builder', action='store_true', help='explicitly execute the project assembler in a temporary copy; default is static-only')
    parser.add_argument('--require-reproducible-build', action='store_true', help='mark static-only builder checks DECLARED_UNVERIFIED when reproducible build is required')
    parser.add_argument('--keep-rebuild', action='store_true', help='save _gate_rebuild.json into project dir; default keeps no rebuild artifact')
    parser.add_argument('--greeting-mode', choices=('player_prose', 'prose_plus_director_appendix', 'ai_trigger'), default='player_prose', help='Greeting policy used when validating a temporary rebuild')
    parser.add_argument('-o', '--output', help='write Markdown report')
    args = parser.parse_args(argv)

    try:
        card_path = Path(args.card).expanduser().resolve()
        project_dir = Path(args.project_dir).expanduser().resolve() if args.project_dir else card_path.parent
        status, issues, notes = check_build_sync(
            card_path,
            project_dir,
            require_build=args.require_build,
            keep_rebuild=args.keep_rebuild,
            greeting_mode=args.greeting_mode,
            execute_builder=args.execute_builder,
            reproducibility_required=args.require_reproducible_build,
        )
        warnings = [n[6:] for n in notes if n.startswith('WARN: ')]
        clean_notes = [n for n in notes if not n.startswith('WARN: ')]
        report = make_report(card_path, project_dir, status, issues, warnings, clean_notes)
        if args.output:
            out = Path(args.output).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report, encoding='utf-8')
            print(f'Wrote build sync report: {out}')
        print(report)
        if status == 'FAIL':
            return 1
        if status == 'WARN':
            return 2
        return 0
    except Exception as exc:
        print(f'check_build_sync.py internal error: {exc}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
