---
name: st-character-card-authoring
description: Public Core for validating and exporting SillyTavern card authoring projects.
version: 0.1.0-public-readiness-core-rc2
---

# SillyTavern Character Card Authoring — Public Core

This is a small public Core router. It does not contain private production examples or source-derived novel material.

## Core workflow

```text
project files
  -> static contracts
  -> documentation audit
  -> provenance/review decision
  -> fail-closed public export
  -> artifact audit
```

## Available capability

- **L1 Core validation:** Python, manifests, documentation links, public-tree safety checks, and regression tests.
- **Bundled release infrastructure:** allowlist export, explicit source-to-public overrides, symlink/path/binary rejection, atomic staging, provenance/review contracts, and trace metadata. This is release infrastructure, not the L2 authoring workflow.
- **L2 Authoring workflow:** not bundled in this strict Core; a future neutral Public Authoring Core must provide the project template, card/worldbook workflow, and authoring contracts.
- **Optional capabilities:** native stage routing, preset integration, Hermes integration, and SillyTavern runtime testing are not bundled in this Core.

## Required evidence

A public artifact is not releasable unless all of the following are true:

```text
artifact audit errors = 0
manual review unresolved = 0
provenance unresolved = 0
private paths = 0
secrets = 0
license present = yes
```

`source` findings describe the private production tree. `artifact` findings are release-blocking.

## Commands

```bash
python -m pytest -q
python scripts/doctor.py --root . --format json
python scripts/audit_docs.py --root . --format json
python scripts/audit_public_release.py --root . --kind artifact --format json
python scripts/audit_public_core_integrity.py --skill-root . --format json
```

No command in this Core claims SillyTavern runtime verification. That requires a real host and manual observation.
