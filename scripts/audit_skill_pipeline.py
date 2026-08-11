#!/usr/bin/env python3
"""Static wiring audit for the character-card build and delivery pipeline.

Checks that the documented delivery path remains discoverable and executable:
required scripts/references exist, scripts compile, CLI help works, manifest runner
has a real dry-run plan, and the canonical assembler succeeds in build-sync's
temporary sandbox. It deliberately does not claim SillyTavern runtime behavior
is tested.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import py_compile
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DELIVERY_SCRIPTS = (
    'atomic_write_json.py',
    'analyze_token_load.py',
    'audit_player_agency_modes.py',
    'audit_source_material_coverage.py',
    'audit_greeting_layers.py',
    'audit_greeting_build_wiring.py',
    'audit_manifest_alignment.py',
    'audit_semantic_modules.py',
    'audit_worldbook_triggers.py',
    'check_build_sync.py',
    'enrichment_self_check.py',
    'migrate_card.py',
    'validate_card.py',
    'verify_enrichment_pass.py',
    'verify_simple_stage_route.py',
    'final_delivery_gate.py',
    'run_delivery.py',
)

SHARED_LIBRARY_SCRIPTS = (
    'lib/card_issues.py',
    'lib/validation_profiles.py',
    'lib/worldbook_matcher.py',
    'lib/stage_routing.py',
    'lib/stage_memory.py',
)

REQUIRED_V52_FILES = {
    'references/workflows/v5.2-validation-and-migration.md': 'v5.2 workflow reference exists',
    '.github/workflows/test.yml': 'v5.2 regression workflow exists',
    'tests/fixtures/valid_ccv3_core_minimal.json': 'v5.2 fixture exists',
    'tests/test_ccv3_profiles.py': 'v5.2 profile regression test exists',
    'tests/test_build_sync.py': 'v5.2 build-sync regression test exists',
    'templates/build-manifest.example.json': 'manifest-driven delivery template exists',
}

REQUIRED_PLAYER_AGENCY_FILES = {
    'templates/player-agency-modes.example.json': 'player-agency template exists',
    'tests/test_player_agency_modes.py': 'player-agency audit regression tests exist',
}

REQUIRED_GREETING_WIRING_FILES = {
    'tests/test_greeting_build_wiring.py': 'Greeting build-wiring regression tests exist',
}

REQUIRED_SEMANTIC_FILES = {
    'references/design-patterns/semantic-modular-open-card-architecture.md': 'semantic modular architecture reference exists',
    'templates/semantic-module-manifest.example.json': 'semantic module manifest template exists',
    'tests/test_semantic_module_pipeline.py': 'semantic module pipeline regression tests exist',
}

REQUIRED_REFERENCES = (
    'references/design-patterns/g-type-toggle-and-natural-trigger-contract.md',
    'references/workflows/card-assembly-and-delivery-pipeline.md',
    'references/workflows/controlled-enrichment-pass.md',
    'references/workflows/source-first-material-and-player-agency-contract.md',
    'references/workflows/v5.2-validation-and-migration.md',
    'references/workflows/manifest-driven-delivery.md',
    'references/design-patterns/greeting-director-appendix-standard.md',
    'references/design-patterns/semantic-modular-open-card-architecture.md',
)

REQUIRED_PIPELINE_TEXT = (
    '<card-skill>/scripts/final_delivery_gate.py',
    '<card-skill>/scripts/run_delivery.py',
    'build_manifest.json',
    'audit_player_agency_modes.py',
    'audit_source_material_coverage.py',
    'audit_greeting_layers.py',
    'audit_greeting_build_wiring.py',
    'greeting_mode=prose_plus_director_appendix',
    'build/greetings.json',
    '源Greeting审查失败时不得继续',
    '--greeting-layer-audit',
    '--greeting-appendix-standard',
    'Greeting build wiring',
    '--source',
    '--source-coverage-minimum',
    '--require-player-agency-modes',
    '--require-build',
    '--enrichment-baseline',
    '--enrichment-manifest',
    '--simple-stage-route',
    '--preset-policy',
    '--native-stage-routing',
    'standalone-card-stage-routing',
    'semantic_manifest',
    'audit_manifest_alignment.py',
    'audit_semantic_modules.py',
)

REQUIRED_SKILL_TEXT = (
    'card-assembly-and-delivery-pipeline.md',
    'manifest-driven-delivery.md',
    'v5.2-validation-and-migration.md',
    'final_delivery_gate.py',
    'audit_player_agency_modes.py',
    'audit_greeting_layers.py',
    'audit_greeting_build_wiring.py',
    'audit_skill_pipeline.py',
    'source-first-material-and-player-agency-contract.md',
    'build_manifest.json',
    'run_delivery.py',
    'greeting_mode=prose_plus_director_appendix',
    'stage_brief_v1',
    'greeting-director-appendix-standard.md',
    'semantic-modular-open-card-architecture.md',
    'semantic-module-manifest.example.json',
    'semantic_manifest',
    'audit_manifest_alignment.py',
    'audit_semantic_modules.py',
)

REQUIRED_FINAL_FLAGS = (
    '--source',
    '--source-coverage-minimum',
    '--require-build',
    '--execute-builder',
    '--require-player-agency-modes',
    '--greeting-layer-audit',
    '--greeting-appendix-standard',
    '--greeting-mode',
    '--legacy-player-agency-modes',
    '--enrichment-baseline',
    '--enrichment-manifest',
    '--simple-stage-route',
    '--native-stage-routing',
    '--preset',
    '--preset-policy',
    '--stage-entry-contract',
)


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def check(self, ok: bool, message: str) -> None:
        (self.notes if ok else self.errors).append(message)


def _run_help(script: Path) -> tuple[bool, str]:
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # Pin both sides of the pipe to UTF-8: mixed parent-GBK/child-UTF-8 shells
    # otherwise kill the capture reader thread and silently blank the output
    # (returncode stays 0), turning decode trouble into bogus flag errors.
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run(
        [sys.executable, str(script), '--help'],
        text=True,
        encoding='utf-8',
        errors='replace',
        capture_output=True,
        timeout=20,
        env=env,
    )
    details = (proc.stdout or '') + (proc.stderr or '')
    return proc.returncode == 0, details


def _compile_without_source_cache(script: Path) -> None:
    """Compile to a disposable cfile so auditing never writes __pycache__ into a skill."""
    with tempfile.TemporaryDirectory(prefix='st_pipeline_compile_') as td:
        cfile = Path(td) / f'{script.stem}.pyc'
        py_compile.compile(str(script), cfile=str(cfile), doraise=True)


def _load_local_module(name: str, path: Path):
    """Load a script in-process without writing __pycache__ into the skill,
    with its parent directory on sys.path so `lib.*` imports resolve regardless
    of the caller's environment."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    parent = str(path.parent)
    old_flag = sys.dont_write_bytecode
    # Scripts use namespace-style `lib.*` imports.  Do not leave that temporary
    # package rooted at this skill after the audit: pytest and another skill can
    # otherwise resolve later imports against a removed sys.path entry.
    old_lib_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == 'lib' or key.startswith('lib.')
    }
    sys.dont_write_bytecode = True
    sys.path.insert(0, parent)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    finally:
        if sys.path and sys.path[0] == parent:
            sys.path.pop(0)
        for key in [key for key in sys.modules if key == 'lib' or key.startswith('lib.')]:
            sys.modules.pop(key, None)
        sys.modules.update(old_lib_modules)
        sys.dont_write_bytecode = old_flag
    return module


def _audit_manifest_runner(skill_root: Path, result: Result) -> None:
    """Exercise the documented default path without claiming a content fixture is deliverable.

    This catches drift among the example manifest, runner CLI, parser, and
    documented dry-run behavior. Full final-gate content policy remains covered
    by its dedicated fixtures.
    """
    runner = skill_root / 'scripts' / 'run_delivery.py'
    template = skill_root / 'templates' / 'build-manifest.example.json'
    fixture = skill_root / 'tests' / 'fixtures' / 'valid_leyu_manual_toggle.json'
    if not all(path.is_file() for path in (runner, template, fixture)):
        result.errors.append('manifest runner smoke prerequisites missing (runner/template/fixture)')
        return

    try:
        raw = json.loads(template.read_text(encoding='utf-8-sig'))
        runner_mod = _load_local_module('manifest_runner_protocol_audit', runner)
        runner_mod.load_delivery_manifest(template)
        result.check(
            isinstance(raw, dict),
            'manifest template parses as JSON and passes runner schema validation',
        )
    except Exception as exc:
        result.errors.append(f'manifest template/runner schema smoke test failed: {exc}')
        return

    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        proc = subprocess.run(
            [sys.executable, str(runner), str(fixture), '--manifest', str(template), '--dry-run'],
            text=True,
            encoding='utf-8',
            errors='replace',
            capture_output=True,
            timeout=30,
            env=env,
        )
    except Exception as exc:
        result.errors.append(f'manifest runner dry-run ERROR: {exc}')
        return
    output = (proc.stdout or '') + (proc.stderr or '')
    required = ('有效交付计划：', 'card validation: RUN', 'source coverage: SKIP', 'final gate argv:')
    if proc.returncode == 0 and all(marker in output for marker in required):
        result.notes.append('manifest runner dry-run PASS: template → run_delivery.py → effective plan')
    else:
        result.errors.append(
            'manifest runner dry-run FAIL: expected effective-plan markers; '
            f'exit={proc.returncode}; output={output[-1200:]}'
        )


def _audit_canonical_build_fixture(skill_root: Path, result: Result) -> None:
    """Run the documented assembler path in its non-destructive build-sync sandbox."""
    sync_script = skill_root / 'scripts' / 'check_build_sync.py'
    project = skill_root / 'references' / 'audit' / 'fixtures' / 'good_build_nested'
    card = project / 'good_build_nested.json'
    if not all(path.is_file() for path in (sync_script, card)):
        result.errors.append('canonical build fixture smoke prerequisites missing (check_build_sync/fixture card)')
        return
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        proc = subprocess.run(
            [
                sys.executable, str(sync_script), str(card),
                '--project-dir', str(project), '--require-build', '--execute-builder',
            ],
            text=True,
            encoding='utf-8',
            errors='replace',
            capture_output=True,
            timeout=60,
            env=env,
        )
    except Exception as exc:
        result.errors.append(f'canonical build fixture assembly sync ERROR: {exc}')
        return
    output = (proc.stdout or '') + (proc.stderr or '')
    if proc.returncode in {0, 2} and 'assemble验证通过' in output and '## Errors' not in output:
        result.notes.append('canonical build fixture assembly sync PASS: assemble_card.py → build sync')
    else:
        result.errors.append(
            'canonical build fixture assembly sync FAIL: '
            f'exit={proc.returncode}; output={output[-1200:]}'
        )


def _audit_semantic_pipeline(skill_root: Path, result: Result) -> None:
    """Exercise the opt-in semantic manifest through the unified runner."""
    runner = skill_root / 'scripts' / 'run_delivery.py'
    semantic_script = skill_root / 'scripts' / 'audit_semantic_modules.py'
    template = skill_root / 'templates' / 'semantic-module-manifest.example.json'
    if not all(path.is_file() for path in (runner, semantic_script, template)):
        result.errors.append('semantic pipeline smoke prerequisites missing (runner/semantic audit/template)')
        return
    try:
        semantic_template = json.loads(template.read_text(encoding='utf-8-sig'))
        runner_mod = _load_local_module('semantic_pipeline_runner_audit', runner)
        semantic_mod = _load_local_module('semantic_pipeline_semantic_audit', semantic_script)
        result.check(semantic_template.get('semantic_profile') == 'modular_semantic_v1', 'semantic manifest template declares modular_semantic_v1')
        with tempfile.TemporaryDirectory(prefix='st_semantic_pipeline_') as td:
            root = Path(td)
            build = root / 'build'
            build.mkdir()
            role_text = '# 角色模块：示例角色｜核心心理与性格\n\n## 条目作用\n\n描述稳定心理。\n\n## 核心锚点\n\n- 核心需求：保持判断权。\n\n## 触发与响应\n\n根据现场压力选择试探或有限回应。\n\n## 具体表现\n\n先观察，再回应。\n\n## 特质交叠\n\n谨慎与好奇同时存在。\n\n## 语言与称谓\n\n保持正式称谓。\n\n## 信息边界\n\n只使用已确认信息。\n\n## 不应误写\n\n不替玩家决定。\n\n## 可开放变化\n\n反应强度可以变化。'
            place_text = '# 地点模块：示例地点\n\n## 条目作用\n\n描述地点的可用范围。\n\n## 地点定位\n\n用于交谈和观察。\n\n## 启用时间\n\n当前场景即可自然到达。\n\n## 空间布局\n\n入口、公开区和内侧空间。\n\n## 自然入口\n\n通过营业、门或熟人进入。\n\n## 现实规则\n\n门禁、旁观者和退出路径有效。\n\n## 场景边界\n\n不可逆结果需要互动前提。\n\n## 剧情功能\n\n承载调查与候选入口。\n\n## 不应误写\n\n不无前提切换地点。\n\n## 可开放变化\n\n人员分布和停留顺序可以变化。'
            entries = []
            for character, metadata in semantic_template.get('characters', {}).items():
                for module_name in metadata.get('modules', []):
                    entries.append({'comment': f'角色/{character}/{module_name}', 'content': role_text})
            for comment in semantic_template.get('world_modules', []):
                entries.append({'comment': comment, 'content': place_text if '/地点/' in comment else role_text})
            card = {'data': {'character_book': {'entries': entries}}}
            card_path = root / 'card.json'
            card_path.write_text(json.dumps(card, ensure_ascii=False), encoding='utf-8')
            semantic = json.loads(json.dumps(semantic_template, ensure_ascii=False))
            semantic_path = build / 'semantic-module-manifest.json'
            semantic_path.write_text(json.dumps(semantic, ensure_ascii=False), encoding='utf-8')
            build_manifest_path = root / 'build_manifest.json'
            build_manifest_path.write_text(json.dumps({'schema_version': 1, 'prototype': 'A', 'routing_mode': 'flat', 'runtime_driver': 'native_st', 'runtime_state': {'authority': 'none'}, 'greeting_mode': 'player_prose', 'semantic_manifest': 'build/semantic-module-manifest.json'}), encoding='utf-8')
            plan = runner_mod.build_delivery_plan(card_path, build_manifest_path)
            result.check(any(check.name == 'manifest alignment' and check.status == 'RUN' for check in plan.checks), 'manifest alignment is RUN by unified delivery plan')
            result.check(any(check.name == 'semantic module audit' and check.status == 'RUN' for check in plan.checks), 'semantic manifest is RUN by unified delivery plan')
            result.check(any(check.name == 'semantic text audit' and check.status == 'RUN' for check in plan.checks), 'semantic text audit is RUN by unified delivery plan')
            result.check(runner_mod.run_semantic_audit(card_path, build_manifest_path) == [], 'semantic positive fixture passes the internal semantic audit function')
            semantic.pop('authoritative_route')
            semantic_path.write_text(json.dumps(semantic, ensure_ascii=False), encoding='utf-8')
            bad = runner_mod.run_semantic_audit(card_path, build_manifest_path)
            result.check(any(issue.get('code') == 'MISSING_PROJECT_CONTRACT' for issue in bad), 'semantic negative fixture is rejected before final gate')
            semantic.pop('authoritative_route', None)
            semantic.pop('semantic_profile', None)
            semantic_path.write_text(json.dumps(semantic, ensure_ascii=False), encoding='utf-8')
            profile_bad = runner_mod.run_semantic_audit(card_path, build_manifest_path)
            result.check(any(issue.get('code') == 'SEMANTIC_PROFILE_MISMATCH' for issue in profile_bad), 'declared semantic manifest without profile is rejected')
            result.check(any(issue.get('level') == 'ERROR' for issue in semantic_mod.audit(card, semantic, require_profile=True)), 'semantic audit reports structured ERROR issues')
    except Exception as exc:
        result.errors.append(f'semantic pipeline smoke test failed: {type(exc).__name__}: {exc}')


def _audit_stage_protocol(skill_root: Path, result: Result) -> None:
    """Validate the protocol's real parser, matcher, documented command, and the
    sibling scripts final_delivery_gate actually executes at runtime."""
    contract_script = skill_root / 'scripts/audit_stage_entry_contracts.py'
    template = skill_root / 'templates/stage-entry-contract.example.json'
    pipeline = skill_root / 'references/workflows/card-assembly-and-delivery-pipeline.md'
    matcher = skill_root / 'scripts/lib/stage_routing.py'
    sibling_root = skill_root.parent / 'standalone-card-stage-routing'
    sibling_matcher = sibling_root / 'scripts/lib/stage_routing.py'
    sibling_audit = sibling_root / 'scripts/audit_native_stage_architecture.py'
    sibling_script_audit = sibling_root / 'scripts/audit_stage_card_scripts.py'
    preset_audit = skill_root.parent / 'sillytavern-preset-debugging' / 'scripts' / 'audit_st_preset.py'

    sibling_present = sibling_root.is_dir()
    if not sibling_present:
        result.notes.append(
            'WARN: sibling skill standalone-card-stage-routing is not checked out next to this skill '
            '(single-skill checkout?): sibling matcher/auditor checks skipped; '
            'final_delivery_gate reports CAPABILITY_MISSING for native-stage runs in this layout'
        )

    main_targets = ((contract_script, 'stage contract parser'), (template, 'stage contract template'), (matcher, 'canonical stage matcher'))
    sibling_targets = ((sibling_matcher, 'sibling stage matcher'), (sibling_audit, 'sibling native auditor'), (sibling_script_audit, 'sibling stage-script auditor')) if sibling_present else ()
    for path, label in (*main_targets, *sibling_targets):
        result.check(path.is_file(), f'{label} exists: {path}')

    # final_delivery_gate exec_module()s these at runtime: mere existence is not
    # enough, a syntax-broken sibling gate must fail this audit too.
    for path, label in sibling_targets:
        if not path.is_file():
            continue
        try:
            _compile_without_source_cache(path)
            result.notes.append(f'py_compile PASS: {label}')
        except py_compile.PyCompileError as exc:
            result.errors.append(f'py_compile FAIL: {label}: {exc.msg}')
    if preset_audit.is_file():
        try:
            _compile_without_source_cache(preset_audit)
            result.notes.append('py_compile PASS: preset sibling audit_st_preset.py')
        except py_compile.PyCompileError as exc:
            result.errors.append(f'py_compile FAIL: preset sibling audit_st_preset.py: {exc.msg}')
    else:
        result.notes.append('note: preset sibling skill (sillytavern-preset-debugging) not installed; --preset runs report CAPABILITY_MISSING')

    if not all(path.is_file() for path, _label in main_targets):
        return

    try:
        contract_mod = _load_local_module('stage_contract_protocol_audit', contract_script)
        raw, load_errors = contract_mod.load_contract(template)
        result.check(not load_errors and raw is not None, f'formal v2 template parses with real contract loader: {load_errors}')
        if raw is not None:
            _contract, errors = contract_mod._parse_contract(raw)
            result.check(not errors, f'formal v2 template passes real contract schema: {errors}')
    except Exception as exc:
        result.errors.append(f'formal stage contract parser smoke test failed: {exc}')

    try:
        matcher_mod = _load_local_module('stage_matcher_protocol_audit', matcher)
        examples = ('【开场：P2·关系失衡｜作品标识】', '【开场：关系失衡｜P2】')
        for example in examples:
            result.check(matcher_mod.parse_stage_title(example) is not None, f'canonical matcher accepts title: {example}')
        negatives = ('这不是阶段标题', '【开场：P0·一｜X】另起一段【开场：P1·二｜X】')
        for example in negatives:
            result.check(matcher_mod.parse_stage_title(example) is None, f'canonical matcher rejects non/multi-title text: {example[:20]}')
        if sibling_present and sibling_matcher.is_file():
            left = hashlib.sha256(matcher.read_bytes()).hexdigest()
            right = hashlib.sha256(sibling_matcher.read_bytes()).hexdigest()
            result.check(left == right, 'main and sibling stage matcher sources are byte-identical')
    except Exception as exc:
        result.errors.append(f'stage matcher protocol smoke test failed: {exc}')

    if pipeline.is_file():
        text = pipeline.read_text(encoding='utf-8')
        result.check('--stage-entry-contract <project-dir>/stage-entry-contract.json' in text, 'native-stage workflow command includes the required contract argument')
        result.check("Author's Note" in text and '尚未接入' in text, 'workflow explicitly marks Author\'s Note route as not production-supported')


def audit(skill_root: Path) -> Result:
    result = Result()
    skill_md = skill_root / 'SKILL.md'
    scripts_dir = skill_root / 'scripts'

    result.check(skill_md.is_file(), f'SKILL.md exists: {skill_md}')
    if not skill_md.is_file():
        return result
    skill_text = skill_md.read_text(encoding='utf-8')
    for needle in REQUIRED_SKILL_TEXT:
        result.check(needle in skill_text, f'SKILL.md links pipeline entry: {needle}')

    for relative in REQUIRED_REFERENCES:
        result.check((skill_root / relative).is_file(), f'reference exists: {relative}')

    for relative, label in REQUIRED_V52_FILES.items():
        result.check((skill_root / relative).is_file(), f'{label}: {relative}')
    for relative, label in REQUIRED_PLAYER_AGENCY_FILES.items():
        result.check((skill_root / relative).is_file(), f'{label}: {relative}')
    for relative, label in REQUIRED_GREETING_WIRING_FILES.items():
        result.check((skill_root / relative).is_file(), f'{label}: {relative}')
    for relative, label in REQUIRED_SEMANTIC_FILES.items():
        result.check((skill_root / relative).is_file(), f'{label}: {relative}')

    pipeline_path = skill_root / 'references/workflows/card-assembly-and-delivery-pipeline.md'
    if pipeline_path.is_file():
        pipeline_text = pipeline_path.read_text(encoding='utf-8')
        for needle in REQUIRED_PIPELINE_TEXT:
            result.check(needle in pipeline_text, f'pipeline documents required branch/argument: {needle}')

    for filename in DELIVERY_SCRIPTS:
        path = scripts_dir / filename
        result.check(path.is_file(), f'script exists: scripts/{filename}')
        if not path.is_file():
            continue
        try:
            _compile_without_source_cache(path)
            result.notes.append(f'py_compile PASS: scripts/{filename}')
        except py_compile.PyCompileError as exc:
            result.errors.append(f'py_compile FAIL: scripts/{filename}: {exc.msg}')
            continue
        try:
            ok, detail = _run_help(path)
        except Exception as exc:  # timeout/OSError belongs to this static gate
            result.errors.append(f'--help ERROR: scripts/{filename}: {exc}')
            continue
        result.check(ok, f'--help PASS: scripts/{filename}' if ok else f'--help FAIL: scripts/{filename}: {detail}')

    for relative in SHARED_LIBRARY_SCRIPTS:
        path = scripts_dir / relative
        result.check(path.is_file(), f'shared library exists: scripts/{relative}')
        if not path.is_file():
            continue
        try:
            _compile_without_source_cache(path)
            result.notes.append(f'py_compile PASS: scripts/{relative}')
        except py_compile.PyCompileError as exc:
            result.errors.append(f'py_compile FAIL: scripts/{relative}: {exc.msg}')

    _audit_manifest_runner(skill_root, result)
    _audit_canonical_build_fixture(skill_root, result)
    _audit_semantic_pipeline(skill_root, result)
    _audit_stage_protocol(skill_root, result)

    final_gate = scripts_dir / 'final_delivery_gate.py'
    if final_gate.is_file():
        # Real argparse introspection: --help substring matching was vacuous for
        # flags whose names appear inside other flags' names or help strings.
        try:
            gate_mod = _load_local_module('final_gate_flag_audit', final_gate)
            option_strings = {
                option
                for action in gate_mod.build_parser()._actions
                for option in action.option_strings
            }
            for flag in REQUIRED_FINAL_FLAGS:
                result.check(flag in option_strings, f'final_delivery_gate exposes {flag} (argparse introspection)')
        except Exception as exc:
            result.errors.append(f'final_delivery_gate flag introspection failed: {exc}')

    return result


def render(skill_root: Path, result: Result) -> str:
    status = 'PASS' if not result.errors else 'FAIL'
    error_lines = [f'- {x}' for x in result.errors] or ['- none']
    lines = [
        f'# Character-card delivery pipeline static audit - {status}',
        '',
        f'- skill root: `{skill_root}`',
        '- scope: workflow wiring + isolated fixture smoke tests; does not replace full pytest or SillyTavern runtime verification.',
        '',
        '## Errors',
        *error_lines,
        '',
        '## Checks',
        *(f'- {x}' for x in result.notes),
    ]
    return '\n'.join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Audit character-card delivery pipeline static wiring')
    parser.add_argument('--skill-root', help='character-card skill directory; default: parent of this script directory')
    parser.add_argument('-o', '--output', help='optional Markdown report path')
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.skill_root).expanduser().resolve() if args.skill_root else Path(__file__).resolve().parents[1]
    result = audit(root)
    report = render(root, result)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding='utf-8')
        print(f'Wrote pipeline audit report: {out}')
    print(report)
    return 1 if result.errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
