#!/usr/bin/env python3
"""
Final delivery gate for SillyTavern character cards.

This is a judge, not a fixer. It aggregates existing validators and writes a
Markdown report with a clear delivery verdict.

Exit codes:
  0 = pass
  1 = error/red/build desync
  2 = only warnings / manual confirmation required (a report file is always written)
  3 = gate internal error
  4 = CLI usage error (no gates ran, no report written)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from lib.card_issues import Issue, has_distinct_blocking_warning_threshold, stable_legacy_rule_id
from lib.stage_routing import (
    ROUTE_STAGE_RE,
    card_entries,
    card_data,
    greeting_texts,
    has_native_stage_routing,
    route_stage_markers,
)

SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass
class GateResult:
    name: str
    status: str  # PASS / WARN / FAIL / N/A
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    report_path: str = ''


def import_script(name: str):
    path = SCRIPT_DIR / f'{name}.py'
    return import_script_path(name, path)


def import_script_path(name: str, path: Path):
    """Import a known local gate without relying on the caller's cwd."""
    if not path.exists():
        raise RuntimeError(f'gate script not found: {path}')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def sibling_skill_script(skill_name: str, script_name: str) -> Path:
    """Resolve an installed sibling skill under the same category directory."""
    return SCRIPT_DIR.parent.parent / skill_name / 'scripts' / script_name


def load_card(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    card = json.loads(path.read_text(encoding='utf-8'))
    data = card.get('data', card)
    book = data.get('character_book') or card.get('character_book') or {}
    entries = book.get('entries', [])
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        entries = []
    return card, data, entries


def detect_stage_routing(card: Dict[str, Any]) -> bool:
    """Detect native Greeting-title routing from declarations, not existing bindings.

    Greeting titles are the route declaration.  Looking only at ``entries[].keys``
    would use the property being audited (correct title binding) to decide whether
    the audit should run, allowing greeting-only misbindings to skip the contract.
    """
    return has_native_stage_routing(card)


ROUTE_STAGE_MARKER_RE = ROUTE_STAGE_RE


def detect_external_route_markers(card: Dict[str, Any]) -> List[str]:
    """Detect unsupported external ROUTE_STAGE markers in all model-visible fields."""
    data = card_data(card)
    evidence: List[str] = []
    for entry in card_entries(card):
        values = [*route_stage_markers(entry)]
        # Some legacy ST exports serialize a single primary key as `key` rather
        # than `keys`; it is still model-visible and must not bypass this guard.
        legacy_key = str(entry.get('key', ''))
        if legacy_key and ROUTE_STAGE_MARKER_RE.search(legacy_key):
            values.append(legacy_key)
        for value in values:
            marker = ROUTE_STAGE_MARKER_RE.search(value)
            if marker:
                evidence.append(f"entry[{entry.get('id')}] 含 ROUTE_STAGE 标记: {marker.group(0)}")
    for index, text in enumerate(greeting_texts(card)):
        if ROUTE_STAGE_MARKER_RE.search(text):
            evidence.append(f'greeting[{index}] 含 ROUTE_STAGE=P# 标记')
    return list(dict.fromkeys(evidence))


def run_card_json_preflight(card_path: Path) -> GateResult:
    """Make malformed/BOM card input a normal delivery failure, never exit 3."""
    try:
        raw = card_path.read_bytes()
    except OSError as exc:
        return GateResult('card JSON preflight', 'FAIL', [f'cannot read card: {exc}'])
    errors: List[str] = []
    if raw.startswith(b'\xef\xbb\xbf'):
        errors.append('UTF-8 BOM present; ST import can reject BOM JSON')
    try:
        value = json.loads(raw.decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f'card JSON cannot be parsed: {exc}')
        value = None
    if value is not None and not isinstance(value, dict):
        errors.append('card JSON root must be an object')
    return GateResult('card JSON preflight', 'FAIL' if errors else 'PASS', errors)


def result_status(errors: Sequence[str], warnings: Sequence[str]) -> str:
    if errors:
        return 'FAIL'
    if warnings:
        return 'WARN'
    return 'PASS'


def enrichment_warning_issue(message: str) -> Issue:
    """Assign repeatable rule IDs to legacy enrichment warnings for aggregation."""
    patterns = (
        ("缺少安全等级", "ENRICHMENT_SCENE_SAFETY_LEVEL_MISSING"),
        ("行为链偏少", "ENRICHMENT_BEHAVIOR_CHAIN_THIN"),
        ("缺少独立描写库", "ENRICHMENT_DESCRIPTION_CORPUS_MISSING"),
        ("语料库", "ENRICHMENT_DIALOGUE_CORPUS_THIN"),
        ("事件种子", "ENRICHMENT_EVENT_SEED_THIN"),
        ("缺少行为触发条件", "ENRICHMENT_STAGE_TRIGGER_MISSING"),
        ("核心关系", "ENRICHMENT_RELATIONSHIP_THIN"),
    )
    for marker, rule_id in patterns:
        if marker in message:
            return Issue(rule_id, "warning", "enrichment", message, "leyu-production", True)
    return Issue(stable_legacy_rule_id("ENRICHMENT_WARNING", message), "warning", "enrichment", message, "leyu-production", True)


def run_validate(card_path: Path, greeting_mode: str = 'player_prose') -> GateResult:
    mod = import_script('validate_card')
    ok, errors, warnings = mod.validate_card(str(card_path), greeting_mode=greeting_mode)
    return GateResult('validate_card.py', 'PASS' if ok and not warnings else ('FAIL' if not ok else 'WARN'), errors, warnings)


def run_greeting_layer_audit(
    card_path: Path,
    min_cn: int = 1400,
    max_cn: int = 1800,
    appendix_standard: str = 'none',
) -> GateResult:
    """Run the hybrid Greeting body/appendix gate when explicitly required.

    The gate is opt-in because pure player-prose and pure ai-trigger Greetings are
    legitimate alternatives. For ``prose_plus_director_appendix`` cards the
    delivery workflow must pass ``--greeting-layer-audit``. Stage-brief cards
    additionally pass ``--greeting-appendix-standard stage_brief_v1``.
    """
    mod = import_script('audit_greeting_layers')
    try:
        card = json.loads(card_path.read_text(encoding='utf-8-sig'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return GateResult('audit_greeting_layers.py', 'FAIL', [f'cannot parse card for Greeting layer audit: {exc}'])
    greetings = mod.get_greetings(card)
    if not greetings:
        return GateResult('audit_greeting_layers.py', 'FAIL', ['未找到 first_mes 或 alternate_greetings'])
    audited = [mod.audit_one(text, label, min_cn, max_cn, appendix_standard) for label, text in greetings]
    errors: List[str] = []
    warnings: List[str] = []
    notes = [f"{item['label']}: body_cjk={item['body_cjk']}, appendix_chars={item['appendix_chars']}" for item in audited]
    for item in audited:
        for issue in item['issues']:
            message = f"[{item['label']}] {issue['code']}: {issue['message']}"
            if issue['severity'] == 'error':
                errors.append(message)
            else:
                warnings.append(message)
    return GateResult('audit_greeting_layers.py', result_status(errors, warnings), errors, warnings, notes)


def run_greeting_build_wiring(
    card_path: Path,
    project_dir: Path,
    min_cn: int = 1400,
    max_cn: int = 1800,
    appendix_standard: str = 'none',
) -> GateResult:
    """Verify clean build Greeting sources survive into the assembled card."""
    mod = import_script('audit_greeting_build_wiring')
    result = mod.audit_build_wiring(card_path, project_dir, min_cn, max_cn, appendix_standard)
    return GateResult(
        'audit_greeting_build_wiring.py',
        result['status'],
        result.get('errors', []),
        result.get('warnings', []),
        result.get('notes', []),
    )


def run_audit(card_path: Path, report_dir: Path) -> GateResult:
    mod = import_script('audit_worldbook_triggers')
    card, data, entries = mod.load_card(card_path)
    sources = mod.build_sources(data)
    audits = mod.analyze_entries(entries, sources)
    report = mod.make_report(card_path, card, data, entries, audits, sources)
    out = report_dir / f'{card_path.stem}_worldbook_trigger_audit.md'
    out.write_text(report, encoding='utf-8')

    risky = [a for a in audits if a.risks]
    hard = [a for a in risky if any('🔴' in r or '硬泛' in r or '仅extensions' in r or '仅靠硬泛' in r for r in a.risks)]
    errors = [f"[{a.eid}] {a.comment}: {'; '.join(dict.fromkeys(a.risks))}" for a in hard]
    warnings = [f"[{a.eid}] {a.comment}: {'; '.join(dict.fromkeys(a.risks))}" for a in risky if a not in hard]
    stage_errors, stage_warnings = mod.stage_route_findings(audits, sources)
    errors.extend(stage_errors)
    warnings.extend(stage_warnings)
    status = result_status(errors, warnings)
    return GateResult('audit_worldbook_triggers.py', status, errors, warnings[:30], [f'完整报告: {out}'], str(out))


def run_stage_entry_contract(card_path: Path, contract_path: Path) -> GateResult:
    """Block delivery when a native Greeting-stage card violates its entry contract."""
    mod = import_script('audit_stage_entry_contracts')
    raw_contract, load_errors = mod.load_contract(contract_path)
    if load_errors or raw_contract is None:
        return GateResult('audit_stage_entry_contracts.py', 'FAIL', load_errors or ['cannot load stage entry contract'])
    try:
        card = json.loads(card_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return GateResult('audit_stage_entry_contracts.py', 'FAIL', [f'cannot parse card for stage contract: {exc}'])
    result = mod.audit_card(card, raw_contract)
    return GateResult(
        'audit_stage_entry_contracts.py',

        result_status(result.errors, result.warnings),
        result.errors,
        result.warnings,
        result.notes,
    )


def run_enrichment(
    card_path: Path,
    r18: bool,
    prototype: str,
    three_path: str,
    policy_manifest: Path | None = None,
) -> GateResult:
    mod = import_script('enrichment_self_check')
    try:
        policy_loader = getattr(mod, 'load_quality_policy', None)
        policy = policy_loader(policy_manifest) if policy_loader is not None else {}
        issues = mod.check_card(
            str(card_path),
            verbose=False,
            r18=r18,
            prototype=prototype,
            three_path=three_path,
            **policy,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return GateResult('enrichment_self_check.py', 'FAIL', [f'content policy读取失败: {exc}'])
    open_policy = (
        policy.get('event_mode') == 'open_situation_seed'
        and policy.get('corpus_mode') == 'curated_anchor_set'
        and policy.get('route_policy') == 'player_led'
    )
    reds = [m for s, m in issues if s == '🔴']
    yellows = [m for s, m in issues if s == '🟡']
    notes = [m for s, m in issues if s == '✅'][:20]
    errors = list(reds)
    warnings = list(yellows)
    yellow_issues = [enrichment_warning_issue(message) for message in yellows]
    if not errors and not open_policy and has_distinct_blocking_warning_threshold(yellow_issues, threshold=3):
        rule_ids = sorted({issue.rule_id for issue in yellow_issues if issue.blocking})
        errors.append(
            "[BLOCKING_WARNING_THRESHOLD] enrichment_self_check.py has at least three distinct "
            f"blocking warning rules: {', '.join(rule_ids)}"
        )
    status = 'FAIL' if errors else ('PASS' if open_policy else result_status(errors, warnings))
    if open_policy and warnings:
        notes.append(f'open player-led policy: {len(warnings)} enrichment diagnostics retained as non-blocking warnings')
    return GateResult('enrichment_self_check.py', status, errors, warnings, notes)


def run_source_material_coverage(
    card_path: Path,
    sources: Sequence[Path],
    minimum: float | None = None,
    corpus_mode: str = 'legacy_unspecified',
) -> GateResult:
    """Run the canonical-excerpt gate when this delivery explicitly declares sources."""
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        return GateResult('audit_source_material_coverage.py', 'FAIL', [f'canonical source file not found: {path}' for path in missing])
    try:
        mod = import_script('audit_source_material_coverage')
        card = json.loads(card_path.read_text(encoding='utf-8-sig'))
        source = mod.read_source(list(sources))
        result = mod.audit_card_data(card, source)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return GateResult('audit_source_material_coverage.py', 'FAIL', [f'cannot read canonical coverage input: {exc}'])
    coverage_value = result['coverage']
    effective_minimum = minimum if minimum is not None else (0.0 if corpus_mode == 'curated_anchor_set' else 0.60)
    minimum_note = (
        f"minimum={effective_minimum:.1%}"
        if minimum is not None or corpus_mode != 'curated_anchor_set'
        else "minimum=not enforced (curated_anchor_set)"
    )
    notes = [
        'canonical sources: ' + ', '.join(str(path) for path in sources),
        f"eligible={result['eligible']} matched={result['matched']} coverage="
        + (f"{coverage_value:.1%}" if coverage_value is not None else "N/A")
        + f" {minimum_note}",
    ]
    if result.get('status') == 'no_eligible' and not (corpus_mode == 'curated_anchor_set' and minimum is None):
        return GateResult(
            'audit_source_material_coverage.py',
            'FAIL',
            ['SOURCE_COVERAGE_NO_ELIGIBLE_ENTRIES: canonical source coverage was required but no eligible material entry exists'],
            [],
            notes,
        )
    if result.get('status') == 'no_eligible':
        return GateResult(
            'audit_source_material_coverage.py',
            'PASS',
            [],
            [],
            notes + ['curated_anchor_set: no universal excerpt coverage minimum'],
        )
    coverage = float(coverage_value)
    if result['unmatched_ids']:
        notes.append('unmatched_ids=' + ','.join(map(str, result['unmatched_ids'])))
    if corpus_mode == 'curated_anchor_set' and minimum is None:
        return GateResult(
            'audit_source_material_coverage.py',
            'PASS',
            [],
            [],
            notes + ['curated_anchor_set: no universal excerpt coverage minimum'],
        )
    errors = [] if coverage >= effective_minimum else [f'CANONICAL_SOURCE_COVERAGE_LOW: coverage={coverage:.1%} < minimum={effective_minimum:.1%}']
    return GateResult('audit_source_material_coverage.py', 'FAIL' if errors else 'PASS', errors, [], notes)


def run_player_agency_modes(
    card_path: Path,
    require_modes: bool = True,
    require_boundary: bool = False,
    require_boundary_always_on: bool = False,
) -> GateResult:
    """Enforce the opt-in director plus player-agency boundary contract."""
    mod = import_script('audit_player_agency_modes')
    result = mod.audit_entries(
        mod.load_entries(card_path),
        require_modes=require_modes,
        require_boundary=require_boundary,
        require_boundary_always_on=require_boundary_always_on,
    )
    return GateResult(
        'audit_player_agency_modes.py',
        result_status(result.errors, result.warnings),
        result.errors,
        result.warnings,
        result.notes,
    )


def run_controlled_enrichment_pass(card_path: Path, baseline_path: Path, manifest_path: Path) -> GateResult:
    """Optional baseline-diff gate for a scoped content-enrichment revision."""
    mod = import_script('verify_enrichment_pass')
    baseline = mod.load_json(baseline_path)
    candidate = mod.load_json(card_path)
    manifest = mod.load_json(manifest_path)
    errors, notes, summary = mod.verify(baseline, candidate, manifest)
    notes = [
        f"allowed IDs={summary['allowed_ids']}",
        f"changed IDs={summary['changed_ids']}",
        f"total content delta={summary['total_content_delta']} chars",
        *notes,
    ]
    return GateResult('verify_enrichment_pass.py', 'FAIL' if errors else 'PASS', errors, [], notes)


def run_simple_stage_route(card_path: Path) -> GateResult:
    """Optional card-side contract for the paired-preset `阶段P#` route variant."""
    mod = import_script('verify_simple_stage_route')
    errors, notes, _summary = mod.audit_card(
        card_path,
        stages=list(range(7)),
        marker_prefix='阶段P',
        scan_depth=2,
        forbidden=['ROUTE_STAGE', 'ROUTE_MODE', '当前阶段：'],
    )
    return GateResult('verify_simple_stage_route.py', 'FAIL' if errors else 'PASS', errors, [], notes)


def run_preset_static_audit(preset_path: Path, policy_path: Path, strict_mismatch: bool) -> GateResult:
    """Run the sibling preset gate when this card ships with a paired preset."""
    script = sibling_skill_script('sillytavern-preset-debugging', 'audit_st_preset.py')
    if not script.exists():
        return GateResult(
            'audit_st_preset.py',
            'FAIL',
            [f'[CAPABILITY_MISSING] paired preset audit requires sibling skill script: {script}'],
        )
    mod = import_script_path('audit_st_preset_for_delivery', script)
    preset, preset_bom = mod.load_json(preset_path)
    policy, policy_bom = mod.load_json(policy_path)
    errors, warnings, notes = mod.audit(preset, preset_bom, policy, strict_mismatch)
    if policy_bom:
        warnings.append('policy JSON contains UTF-8 BOM; harmless to ST but normalize it for reproducible review')
    return GateResult('audit_st_preset.py', result_status(errors, warnings), errors, warnings, notes)


def run_native_stage_routing(card_path: Path, *, stage_manifest: dict[str, Any] | None = None) -> List[GateResult]:
    """Run native-title script checks; contract cards use the architecture audit with a dynamic manifest.

    Without a stage_manifest the architecture auditor falls back to its legacy
    P0-P6 default.  When the caller provides a dynamic manifest derived from a
    stage-entry contract the architecture audit uses that project's real stages
    instead.
    """
    architecture_script = sibling_skill_script('standalone-card-stage-routing', 'audit_native_stage_architecture.py')
    script_audit_script = sibling_skill_script('standalone-card-stage-routing', 'audit_stage_card_scripts.py')
    required_scripts = [architecture_script, script_audit_script]
    missing = [path for path in required_scripts if not path.exists()]
    if missing:
        return [
            GateResult(
                script.name,
                'FAIL',
                [f'[CAPABILITY_MISSING] native-stage delivery audit requires sibling skill script: {script}'],
            )
            for script in missing
        ]
    raw = card_path.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        bom_error = ['JSON contains UTF-8 BOM; ST import can reject BOM JSON']
        return [GateResult(script.name, 'FAIL', bom_error) for script in required_scripts]
    card = json.loads(raw.decode('utf-8'))
    results: List[GateResult] = []
    architecture = import_script_path('audit_native_stage_architecture_for_delivery', architecture_script)
    architecture_kwargs: dict[str, Any] = {}
    if stage_manifest is not None:
        architecture_kwargs['manifest'] = stage_manifest
    result_a = architecture.audit_card(card, **architecture_kwargs)
    results.append(
        GateResult(
            'audit_native_stage_architecture.py',
            result_status(result_a.failures, result_a.warnings),
            result_a.failures,
            result_a.warnings,
            result_a.passes,
        )
    )
    script_audit = import_script_path('audit_stage_card_scripts_for_delivery', script_audit_script)
    result_b = script_audit.audit_card(card)
    results.append(
        GateResult(
            'audit_stage_card_scripts.py',
            result_status(result_b.failures, result_b.warnings),
            result_b.failures,
            result_b.warnings,
            result_b.passes,
        )
    )
    return results


def run_build_sync(
    card_path: Path,
    project_dir: Path,
    require_build: bool,
    greeting_mode: str = 'player_prose',
    execute_builder: bool = False,
    reproducibility_required: bool = False,
) -> GateResult:
    mod = import_script('check_build_sync')
    status, issues, notes = mod.check_build_sync(
        card_path,
        project_dir,
        require_build=require_build,
        greeting_mode=greeting_mode,
        execute_builder=execute_builder,
        reproducibility_required=reproducibility_required,
    )
    mapped = 'FAIL' if status == 'FAIL' else ('N/A' if status == 'N/A' else ('WARN' if status == 'WARN' else 'PASS'))
    warnings = [n[6:] for n in notes if isinstance(n, str) and n.startswith('WARN: ')]
    clean_notes = [n for n in notes if not (isinstance(n, str) and n.startswith('WARN: '))]
    return GateResult('check_build_sync.py', mapped, issues, warnings, clean_notes)


def collect_strings(obj: Any) -> List[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, list):
        out: List[str] = []
        for item in obj:
            out.extend(collect_strings(item))
        return out
    if isinstance(obj, dict):
        out: List[str] = []
        for item in obj.values():
            out.extend(collect_strings(item))
        return out
    return []


def scan_forbidden(card_path: Path, r18: bool, strict_age: bool = False, strict_platform: bool = False, publish_text: Path | None = None) -> GateResult:
    raw = card_path.read_text(encoding='utf-8', errors='ignore')
    try:
        decoded = '\n'.join(collect_strings(json.loads(raw)))
    except Exception:
        decoded = ''
    # Residue scan checks the card JSON because build/code leftovers are card-quality issues.
    # Platform/age scans do NOT inspect card JSON: Discord/community moderation only sees the
    # posted intro/thread text, not the embedded card/worldbook JSON. Card creation must remain
    # unaffected by novel-source sensitive words or fictional ages.
    scan_text = decoded if decoded else raw

    # Community publish checks are about underage/child-coded wording in the intro/post.
    # Non-age NSFW words inside the card are not platform-blocking for this workflow.
    hard_terms = ['萝莉', '幼女', '幼齿', '童贞', 'luoli', 'loli', '未成年']
    errors: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []

    publish_scan_text = ''
    if strict_platform or strict_age:
        if publish_text:
            publish_scan_text = publish_text.read_text(encoding='utf-8', errors='ignore')
            notes.append(f'发布文案扫描: {publish_text}')
        else:
            notes.append('未提供 --publish-text；Discord/社区只审发布简介/帖子文案，不审卡内JSON，已跳过平台/年龄专项扫描')

    if strict_platform and publish_scan_text:
        for term in hard_terms:
            count = len(re.findall(re.escape(term), publish_scan_text, flags=re.I))
            if count:
                errors.append(f'平台严格模式：发布文案社区高风险词 `{term}` 命中 {count} 次')
    if strict_age and publish_scan_text:
        # Do not scan numeric ages. User rule: age < 18 is not itself a blocker;
        # only explicit underage/child-coded wording in the posted intro needs review.
        age_terms = ['未成年', '幼女', '幼齿', '儿童', '恋童', '小学生', '初中生', '高中生']
        for term in age_terms:
            count = publish_scan_text.count(term)
            if count:
                warnings.append(f'严格年龄扫描：发布文案未成年/儿童化词 `{term}` 命中 {count} 次，需人工确认')

    residue_patterns = [
        ('python编码声明残留', r'#\s*-\*-\s*coding[:=]\s*utf-8\s*-\*-'),
        ('import json代码残留', r'(^|\n)\s*import\s+json\b'),
        ('make_entry函数残留', r'\bdef\s+make_entry\s*\('),
        ('event变量赋值残留', r'\bevent_[A-Za-z0-9_]*\s*='),
        ('三引号代码残留', r'("""|\'\'\')'),
        ('pad_to构建残留', r'pad_to'),
        ('PLACEHOLDER/TODO占位残留', r'(?-i:PLACEHOLDER|TODO)'),
        ('Unicode标签残留', r'\[U\+[0-9A-Fa-f]{4,6}\]'),
        ('print调试残留', r'(^|\n)\s*print\s*\('),
    ]
    for label, pattern in residue_patterns:
        count = len(re.findall(pattern, scan_text, flags=re.I | re.M))
        if count:
            errors.append(f'{label} 命中 {count} 次')
    status = result_status(errors, warnings)
    name_parts = []
    if strict_platform:
        name_parts.append('platform-forbidden')
    name_parts.extend(['localization', 'residue'])
    if strict_age:
        name_parts.append('age')
    name = '/'.join(name_parts) + ' scan'
    return GateResult(name, status, errors, warnings, notes)


def format_section(res: GateResult) -> List[str]:
    lines = [f'## {res.name}: {res.status}', '']
    if res.report_path:
        lines.append(f'- report: `{res.report_path}`')
    if res.errors:
        lines.append('### Errors')
        lines.extend(f'- {m}' for m in res.errors[:40])
        if len(res.errors) > 40:
            lines.append(f'- ...+{len(res.errors)-40} more')
        lines.append('')
    if res.warnings:
        lines.append('### Warnings')
        lines.extend(f'- {m}' for m in res.warnings[:40])
        if len(res.warnings) > 40:
            lines.append(f'- ...+{len(res.warnings)-40} more')
        lines.append('')
    if res.notes:
        lines.append('### Notes')
        lines.extend(f'- {m}' for m in res.notes[:25])
        if len(res.notes) > 25:
            lines.append(f'- ...+{len(res.notes)-25} more')
        lines.append('')
    if not (res.errors or res.warnings or res.notes):
        lines.append('- no issues')
        lines.append('')
    return lines


def final_verdict(results: Sequence[GateResult]) -> Tuple[str, int]:
    if any(r.status == 'FAIL' for r in results):
        return '不可交付', 1
    if any(r.status == 'WARN' for r in results):
        return '可人工确认（仅warning）', 2
    return '可交付', 0


def make_report(card_path: Path, project_dir: Path, prototype: str, r18: bool, strict_age: bool, strict_platform: bool, three_path: str, results: Sequence[GateResult], publish_text: Path | None = None) -> Tuple[str, int, str]:
    verdict, exit_code = final_verdict(results)
    lines = [
        f'# 交付门控报告 — {card_path.name}',
        '',
        f'- card: `{card_path}`',
        f'- project_dir: `{project_dir}`',
        f'- publish_text: `{publish_text or "未提供（Discord/社区只审发布文案，不审卡内JSON）"}`',
        f'- prototype: `{prototype or "未指定"}`',
        f'- r18: `{r18}`',
        f'- strict_age: `{strict_age}`',
        f'- strict_platform: `{strict_platform}`',
        f'- three_path: `{three_path}`',
        f'- final verdict: **{verdict}**',
        f'- exit_code: `{exit_code}`',
        '',
        '## Summary',
        '',
        '| Check | Status | Errors | Warnings |',
        '|---|---:|---:|---:|',
    ]
    for r in results:
        lines.append(f'| {r.name} | {r.status} | {len(r.errors)} | {len(r.warnings)} |')
    lines.append('')
    for r in results:
        lines.extend(format_section(r))
    return '\n'.join(lines), exit_code, verdict


class GateArgumentParser(argparse.ArgumentParser):
    """CLI usage errors exit 4 so they can never be read as the exit-2 warnings-only verdict."""

    def error(self, message: str):
        self.print_usage(sys.stderr)
        self.exit(4, f'{self.prog}: error: {message}\n')


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser; exposed so the meta-audit can introspect real option
    strings instead of substring-matching the --help text."""
    parser = GateArgumentParser(description='Run final delivery gate for a SillyTavern character card')
    parser.add_argument('card', help='final card JSON path')
    parser.add_argument('--project-dir', help='project directory; default: card parent')
    parser.add_argument('--prototype', default='', help='card prototype, e.g. A/B/C/D/E/G')
    parser.add_argument('--r18', dest='r18', action='store_true', default=True, help='enable R18 content-shell checks (default for this NSFW card workflow)')
    parser.add_argument('--no-r18', dest='r18', action='store_false', help='disable R18 content-shell checks for non-NSFW/ordinary worldbook audits')
    parser.add_argument('--strict-age', action='store_true', help='optional age/child-coded word warning scan for publish text only; disabled by default and never scans card JSON')
    parser.add_argument('--strict-platform', action='store_true', help='optional platform/community word scan for publish text only; disabled by default and never scans card JSON')
    parser.add_argument('--publish-text', help='Discord/community intro or post text to scan when --strict-age/--strict-platform is set; card JSON itself is not platform-scanned')
    parser.add_argument('--three-path', choices=['auto', 'hard', 'soft', 'none'], default='auto', help='event seed three-path gate mode passed to enrichment_self_check.py')
    parser.add_argument('--source', action='append', default=[], help='canonical novel chapter/source file; repeat to make source coverage a required delivery gate')
    parser.add_argument('--source-coverage-minimum', type=float, default=None, help='explicit minimum canonical excerpt coverage; defaults to 0.60 for legacy/strict and is not enforced for curated_anchor_set')
    parser.add_argument('--require-build', action='store_true', help='fail if build/all_entries.json and assemble_card.py are absent')
    parser.add_argument('--execute-builder', action='store_true', help='explicitly execute the project assembler in a temporary copy; default is static-only')
    parser.add_argument('--require-reproducible-build', action='store_true', help='mark static-only builder checks DECLARED_UNVERIFIED when manifest requires reproducibility')
    parser.add_argument('--require-player-agency-modes', action='store_true', help='require the default opt-in director/player-boundary mode pair even for a non-G card')
    parser.add_argument('--require-player-boundary', action='store_true', help='require only the player-agency boundary mode; useful for player-led open cards')
    parser.add_argument('--greeting-layer-audit', action='store_true', help='require prose_plus_director_appendix Greeting audit: body >=1400 CJK, appendix delimiter/markup, and body pollution scan')
    parser.add_argument('--greeting-appendix-standard', choices=('none', 'stage_brief_v1'), default='none', help='optional director appendix content contract')
    parser.add_argument('--greeting-mode', choices=('player_prose', 'prose_plus_director_appendix', 'ai_trigger'), default='player_prose', help='Greeting contract passed to validate_card.py; non-prose modes do not inherit the player-prose 1400 floor')
    parser.add_argument('--legacy-player-agency-modes', action='store_true', help='grandfather a legacy card that intentionally omits the opt-in director/player-boundary mode pair; overrides automatic G-card enforcement')
    parser.add_argument('--enrichment-baseline', help='baseline card for a controlled enrichment-pass diff gate')
    parser.add_argument('--enrichment-manifest', help='JSON manifest paired with --enrichment-baseline')
    parser.add_argument('--policy-manifest', help='Manifest v2 supplying content policy dimensions to enrichment_self_check.py')
    parser.add_argument('--simple-stage-route', action='store_true', help='paired-preset 阶段P# route: verify card contract and require --preset/--preset-policy')
    parser.add_argument('--native-stage-routing', action='store_true', help='native-title standalone stage card: run architecture and embedded-script gates')
    parser.add_argument('--stage-entry-contract', help='required with --native-stage-routing; JSON runtime-entry contract for native Greeting-stage cards')
    parser.add_argument('--preset', help='paired preset JSON to statically audit')
    parser.add_argument('--preset-policy', help='policy JSON required with --preset; copy the preset-skill template then set IDs')
    parser.add_argument('--preset-strict-mismatch', action='store_true', help='treat unapproved preset prompt/order enabled mismatches as errors')
    parser.add_argument('-o', '--output', help='Markdown report path; default: <project-dir>/<card>_delivery_gate_report.md')
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if bool(args.enrichment_baseline) != bool(args.enrichment_manifest):
        parser.error('--enrichment-baseline and --enrichment-manifest must be supplied together')
    if bool(args.preset) != bool(args.preset_policy):
        parser.error('--preset and --preset-policy must be supplied together')
    if args.simple_stage_route and not args.preset:
        parser.error('--simple-stage-route requires the paired --preset and --preset-policy; a card-only route check is insufficient for delivery')
    if args.simple_stage_route and args.native_stage_routing:
        parser.error('--simple-stage-route and --native-stage-routing describe different routing architectures; choose exactly one')
    if args.native_stage_routing and not args.stage_entry_contract:
        parser.error('--native-stage-routing requires --stage-entry-contract; native stage cards must declare runtime entry responsibilities')
    if args.source_coverage_minimum is not None and not 0 <= args.source_coverage_minimum <= 1:
        parser.error('--source-coverage-minimum must be between 0 and 1')
    if not args.source and args.source_coverage_minimum is not None:
        parser.error('--source-coverage-minimum requires at least one --source')
    # An explicitly supplied contract is also valid for auto-detected stage cards.

    try:
        card_path = Path(args.card).expanduser().resolve()
        project_dir = Path(args.project_dir).expanduser().resolve() if args.project_dir else card_path.parent
        report_dir = project_dir
        report_dir.mkdir(parents=True, exist_ok=True)

        publish_text = Path(args.publish_text).expanduser().resolve() if args.publish_text else None
        enrichment_baseline = Path(args.enrichment_baseline).expanduser().resolve() if args.enrichment_baseline else None
        enrichment_manifest = Path(args.enrichment_manifest).expanduser().resolve() if args.enrichment_manifest else None
        policy_manifest = Path(args.policy_manifest).expanduser().resolve() if args.policy_manifest else None
        policy_route_policy = 'legacy_unspecified'
        if policy_manifest is not None:
            try:
                policy_loader = import_script('enrichment_self_check')
                policy_route_policy = policy_loader.load_quality_policy(policy_manifest).get(
                    'route_policy', 'legacy_unspecified'
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                policy_route_policy = 'legacy_unspecified'
        preset_path = Path(args.preset).expanduser().resolve() if args.preset else None
        preset_policy_path = Path(args.preset_policy).expanduser().resolve() if args.preset_policy else None
        stage_entry_contract = Path(args.stage_entry_contract).expanduser().resolve() if args.stage_entry_contract else None
        source_paths = [Path(raw).expanduser().resolve() for raw in args.source]
        preflight = run_card_json_preflight(card_path)
        results = [preflight]
        if preflight.status != 'FAIL':
            card_for_detection, _data_for_detection, _entries_for_detection = load_card(card_path)
            auto_stage_routing = detect_stage_routing(card_for_detection)
            if auto_stage_routing and not args.simple_stage_route:
                if stage_entry_contract is None:
                    for candidate in (project_dir / 'stage-entry-contract.json', project_dir / 'stage_entry_contract.json'):
                        if candidate.exists():

                            stage_entry_contract = candidate
                            break
                if stage_entry_contract is None:
                    results.append(GateResult(
                        'stage-routing auto-detection',
                        'FAIL',
                        ['STAGE_CONTRACT_REQUIRED: 检测到阶段路由卡，但未找到 stage-entry-contract.json；阶段路由必须经过合同审计。'],
                    ))
            external_route_markers = detect_external_route_markers(card_for_detection)
            if external_route_markers:
                results.append(GateResult(
                    'external-route detection',
                    'FAIL',
                    ['STAGE_EXTERNAL_ROUTE_UNSUPPORTED: 检测到 ROUTE_STAGE=P# 外部路由标记：'
                     + '; '.join(external_route_markers[:5])
                     + "。Author's Note/ROUTE_STAGE 属外部 preset 路线，未接入本门控，"
                       '本门控结论不得作为该类卡的交付证据；native 独立卡请改用完整 Greeting 标题路由'
                       '并提供 stage-entry-contract.json。'],
                ))
            results.extend([
                run_validate(card_path) if args.greeting_mode == 'player_prose' else run_validate(card_path, args.greeting_mode),
            ])
            if source_paths:
                coverage_corpus_mode = 'legacy_unspecified'
                if policy_manifest is not None:
                    try:
                        policy_loader = import_script('enrichment_self_check')
                        coverage_corpus_mode = policy_loader.load_quality_policy(policy_manifest).get(
                            'corpus_mode', 'legacy_unspecified'
                        )
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                        coverage_corpus_mode = 'legacy_unspecified'
                if policy_manifest is None:
                    # Preserve the three-argument seam used by legacy callers and
                    # tests; no Manifest means legacy/strict default semantics.
                    results.append(run_source_material_coverage(
                        card_path,
                        source_paths,
                        args.source_coverage_minimum,
                    ))
                else:
                    results.append(run_source_material_coverage(
                        card_path,
                        source_paths,
                        args.source_coverage_minimum,
                        coverage_corpus_mode,
                    ))
            results.extend([
                run_player_agency_modes(
                    card_path,
                    require_modes=(
                        (args.prototype.strip().upper() == 'G' or args.require_player_agency_modes)
                        and not args.legacy_player_agency_modes
                    ),
                    require_boundary=(
                        (args.require_player_boundary or policy_route_policy == 'player_led')
                        and not args.legacy_player_agency_modes
                    ),
                    require_boundary_always_on=(
                        (args.require_player_boundary or policy_route_policy == 'player_led')
                        and not args.legacy_player_agency_modes
                    ),
                ),
            ])
            if args.greeting_layer_audit:
                results.append(run_greeting_layer_audit(card_path, appendix_standard=args.greeting_appendix_standard))
                if args.require_build:
                    results.append(run_greeting_build_wiring(
                        card_path,
                        project_dir,
                        appendix_standard=args.greeting_appendix_standard,
                    ))
            results.extend([
                run_audit(card_path, report_dir),
                run_enrichment(card_path, args.r18, args.prototype, args.three_path, policy_manifest),
            ])
            if enrichment_baseline and enrichment_manifest:
                results.append(run_controlled_enrichment_pass(card_path, enrichment_baseline, enrichment_manifest))
            if args.simple_stage_route:
                results.append(run_simple_stage_route(card_path))
            if stage_entry_contract is not None and not args.simple_stage_route and not (args.native_stage_routing or auto_stage_routing):
                results.append(GateResult(
                    'stage entry contract intent',
                    'FAIL',
                    ['STAGE_CONTRACT_ROUTE_UNDETECTED: 已显式传入 --stage-entry-contract，但卡未声明原生Greeting阶段标题且未传 --native-stage-routing。合同不会被静默忽略；请修正路由或使用匹配的交付路径。'],
                ))
            if (args.native_stage_routing or auto_stage_routing) and stage_entry_contract:
                results.append(run_stage_entry_contract(card_path, stage_entry_contract))
                contract_mod = import_script('audit_stage_entry_contracts')
                raw_contract, _load_errors = contract_mod.load_contract(stage_entry_contract)
                manifest = None
                manifest_errors: List[str] = []
                if raw_contract is not None:
                    manifest, manifest_errors = contract_mod.architecture_manifest_from_contract(raw_contract)
                if manifest is not None:
                    results.extend(run_native_stage_routing(card_path, stage_manifest=manifest))
                else:
                    # Never fall back to the sibling auditor's legacy P0-P6 default

                    # under fabricated "missing P#" architecture failures.
                    results.append(GateResult(
                        'audit_native_stage_architecture.py',
                        'FAIL',
                        manifest_errors or ['stage entry contract 无法解析为架构 manifest'],
                        notes=['合同无效时不回退 legacy P0-P6 默认审计；sibling 架构与脚本审计未运行'],
                    ))
            if preset_path and preset_policy_path:
                results.append(run_preset_static_audit(preset_path, preset_policy_path, args.preset_strict_mismatch))
            if args.execute_builder:
                if args.require_reproducible_build:
                    build_sync_result = run_build_sync(
                        card_path,
                        project_dir,
                        args.require_build,
                        args.greeting_mode,
                        execute_builder=True,
                        reproducibility_required=True,
                    )
                else:
                    build_sync_result = run_build_sync(
                        card_path,
                        project_dir,
                        args.require_build,
                        args.greeting_mode,
                        execute_builder=True,
                    )
            elif args.require_reproducible_build:
                build_sync_result = run_build_sync(
                    card_path,
                    project_dir,
                    args.require_build,
                    args.greeting_mode,
                    reproducibility_required=True,
                )
            else:
                build_sync_result = run_build_sync(
                    card_path,
                    project_dir,
                    args.require_build,
                    args.greeting_mode,
                )
            results.extend([
                build_sync_result,
                scan_forbidden(card_path, args.r18, strict_age=args.strict_age, strict_platform=args.strict_platform, publish_text=publish_text),
            ])
        report, exit_code, verdict = make_report(card_path, project_dir, args.prototype, args.r18, args.strict_age, args.strict_platform, args.three_path, results, publish_text=publish_text)
        out = Path(args.output).expanduser().resolve() if args.output else report_dir / f'{card_path.stem}_delivery_gate_report.md'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding='utf-8')
        print(f'Wrote final delivery gate report: {out}')
        print(f'final verdict: {verdict} (exit_code={exit_code})')
        for r in results:
            print(f'- {r.name}: {r.status} errors={len(r.errors)} warnings={len(r.warnings)}')
        return exit_code
    except Exception as exc:
        print(f'final_delivery_gate.py internal error: {exc}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
