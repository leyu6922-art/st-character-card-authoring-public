# Changelog

## 0.1.0-leyu-opinionated-workflow

- Established the public repository as Leyu's opinionated personal SillyTavern authoring workflow.
- Declared the bundled authoring workflow in `skill-manifest.json` with the `leyu-workflow` profile.
- Separated the workflow release identity from the nested `release/public-core/` RC2 artifact.
- Documented Hermes as the Agent-host dependency and stage-routing/runtime integrations as optional capabilities.
- Corrected the public repository identity and release manifest metadata.

## Unreleased contract hardening

- Defined `leyu-workflow` as an existing workflow profile and kept `leyu-production` as a distinct existing validator profile.
- Replaced the root Strict Core export/provenance reference with the full workflow export scope and `workflow-provenance-manifest.json`.
- Moved product boundaries and host-dependent limitations out of `current_blockers`; the current blocker list is now empty.
- Added regression coverage for profile resolution and fail-closed workflow provenance export.
