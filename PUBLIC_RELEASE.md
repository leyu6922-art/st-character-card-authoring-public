# Public release boundary

This repository contains Leyu's reusable, validation-first, opinionated workflow for authoring SillyTavern character cards. It is the public, sanitized workflow edition—not a dump of any private production workspace or an official universal standard.

## Removed from the public edition

- private character-card exports and case studies;
- novel files, copied excerpts, and source-derived dialogue;
- local verification notes, personal planning files, and machine-specific paths;
- images, presets, credentials, logs, and private sibling-skill material.

The workflow describes how to use a source that the operator is authorized to process; it does not redistribute any novel or character source material.

## Path placeholders

Examples use portable placeholders instead of a maintainer's filesystem:

- `<SKILL_ROOT>` — this repository or installed skill directory;
- `<PROJECT_DIR>` — a card project directory;
- `<HERMES_HOME>` — the Hermes data directory, when Hermes integration is used;
- `<SILLYTAVERN_ROOT>` — a local SillyTavern installation;
- `<TEMP_DIR>` — an isolated temporary directory.

Replace placeholders in commands for the current operating system. The repository does not require a fixed username, drive letter, cloud-sync layout, or home directory.

## Sensitive-content boundary

Some design patterns discuss NTR/NTL, adult themes, coercion, or other sensitive fictional scenarios. Treat this material as **18+ authoring guidance**. Use only adult characters, respect consent and platform rules, and do not use the workflow to create exploitative or illegal material. No private case or source text is included here.

## Evidence boundary

The automated checks prove file contracts, schema rules, static routing, workflow provenance, and release hygiene. The root workflow export is governed by `public-export-manifest.json` plus `workflow-provenance-manifest.json`; the nested strict Core has separate contracts under `release/public-core/`. These checks do not prove SillyTavern import behavior, model quality, UI rendering, or runtime behavior.

## Public-release checks

```bash
python -m pytest -q
python scripts/audit_public_release.py --root . --kind source --format text
python scripts/audit_public_core_integrity.py --skill-root . --format text
```

Before each tagged release or regenerated public distribution, rebuild and verify the fresh-history artifact itself. A sanitized working tree does not erase sensitive content from old Git commits.
