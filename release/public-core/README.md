# SillyTavern Character Card Authoring — Public Core

**Status: Public Release Infrastructure candidate — RC2; RC1 remains immutable**

This sanitized Core distribution contains only the public-readiness infrastructure created for a clean-room release workflow. It intentionally excludes private production cases, novel text, character-card exports, images, presets, archived audits, and sibling-skill material.

## Included

- fail-closed public export with explicit overrides
- source-vs-artifact release auditing
- machine-readable provenance and review contracts
- clean-room capability doctor
- regression tests for the public-readiness tools

## Quickstart

```bash
python -m pytest -q
python scripts/doctor.py --root . --format json
python scripts/audit_public_release.py --root . --kind artifact --format json
python scripts/audit_public_core_integrity.py --skill-root . --format json
```

The artifact audit is the release gate. A local test pass does not prove SillyTavern runtime behavior, model quality, UI rendering, or optional stage-routing integration.

## Capability boundary

This Core is the public validation and export foundation. Advanced native stage routing, preset integration, Hermes integration, SillyTavern runtime verification, and private authoring profiles are optional or intentionally absent.

Evidence levels are explicit:

```text
SPECIFIED
STATIC_VERIFIED
INTEGRATION_VERIFIED
RUNTIME_VERIFIED
OBSERVED
```

Do not interpret `STATIC_VERIFIED` as real-host runtime acceptance.

## Content and rights boundary

No third-party novel, character, image, preset, or community tutorial content is intentionally included in this Core candidate. Users remain responsible for verifying ownership, redistribution rights, platform rules, and any adult-content obligations before publishing an artifact.

The RC2 candidate has a real MIT license and a resolved Core provenance manifest. It remains a separately versioned strict Core artifact inside the broader `leyu-workflow` distribution; it does not define the parent workflow's release version or claim runtime integrations.
