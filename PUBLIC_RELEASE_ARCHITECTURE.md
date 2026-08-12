# Public Release Architecture

> Status: **CANDIDATE / v0.1.0**
> This document defines the public distribution of Leyu's opinionated authoring workflow. It is an architecture contract, not a promise that every runtime behavior is already verified. The nested `release/public-core/` directory remains a separately versioned strict Core artifact.

## 0. Decisions

1. **Current distribution model:** this repository publishes a fresh-history, sanitized version of Leyu's personal authoring workflow.
2. The workflow includes personal preferences, production heuristics, design patterns, validation scripts, templates, references, and delivery gates; it does not claim to be a universal standard.
3. `release/public-core/` is a narrower, separately versioned strict Core candidate. Its RC2 identity must not be confused with the parent workflow release.
4. The original private production repository remains private.
5. `skill-manifest.json` is the authoritative capability, dependency, profile, and workflow-version contract. `public-export-manifest.json` is the authoritative workflow-distribution boundary and fresh-history contract; `workflow-provenance-manifest.json` is its provenance contract. The nested `release/public-core/` product has separate contracts. README tables, `doctor.py`, CI, and installers must derive from these files or be checked against them.
6. Trust is external to the project being checked. A project manifest must never be able to declare itself trusted.

## 1. Goals and non-goals

### Goals

- Install the core validation and authoring workflow on a clean machine.
- Diagnose which capability level is actually available.
- Rebuild and validate synthetic examples from source to delivery report.
- Make public/private boundaries, dependencies, evidence levels, and release scope machine-readable.
- Preserve compatibility with existing cards and the `leyu-production` profile during migration.

### Non-goals

- Guarantee identical text generation across models or providers.
- Claim SillyTavern runtime verification from static or integration tests.
- Distribute copyrighted novels, private cards, private paths, or unlicensed third-party material.
- Treat a temporary directory as a security sandbox.

## 2. Repository topology

### Current: sanitized opinionated workflow distribution

```text
private production source
        |
        | deterministic allowlist export + public-release audit
        v
public distribution repository (fresh history)
```

The public repository is an independent distribution of the reviewed opinionated workflow. Public changes should be reconciled into the reviewed source process; a blanket copy from the live internal tree is forbidden.

### Future relationship: Core plus Overlay

```text
Public Core
  scripts / schemas / contracts / neutral workflows / tests
        ^
        | dependency
Private Overlay
  personal preferences / private cases / experiments / local adapters
```

The overlay must not redefine Core contracts silently. It may add profiles, examples, and project-specific rules through documented extension points.

## 3. Capability levels

| Level | Name | Capability | Minimum dependencies |
|---|---|---|---|
| L1 | Core Validation | CCv3, Worldbook, Manifest, semantic and delivery validators | This repository |
| L2 | Leyu Authoring Workflow | Agent planning, interview, project design, build, audit, delivery, and personal quality gates | Hermes Agent + this repository |
| L3 | Advanced Routing | Native stage routing, stage-entry contracts, stage memory integration | `standalone-card-stage-routing` |
| L4 | Full Runtime Stack | SillyTavern runtime, preset, extensions, UI/state and real-host checks | SillyTavern + configured extensions + sibling skills |

A missing optional capability must produce `MISSING` or `NOT_CONFIGURED`, never a false `PASS`. Runtime behavior must be reported separately from static and integration evidence.

## 4. Authoritative contracts

`skill-manifest.json` is the single source for:

- capability levels and dependency requirements;
- supported formats and host compatibility;
- profile names and migration status;
- release version and evidence vocabulary.

`public-export-manifest.json` is the single source for:

- public file scope and excluded material for the Leyu workflow distribution;
- redaction and workflow-provenance review rules;
- fresh-history export policy;
- required public-release gates.

`workflow-provenance-manifest.json` resolves the provenance of the bundled workflow distribution. It is separate from `release/public-core/provenance-manifest.json`, which covers only the nested strict Core artifact.

`SKILL.md` remains the Hermes authoring adapter. It should explain how to use the contracts, not silently become a second dependency or release manifest. CI must detect drift between the manifests and derived documentation.

## 5. Trust boundary for build synchronization

`check_build_sync.py` may execute a project-provided `assemble_card.py`. This is arbitrary local Python code, not a sandboxed build.

Required behavior for the public framework:

- static inspection is the safe default;
- executing a builder requires an explicit CLI flag such as `--execute-builder`;
- trust comes from the user/CLI or a trusted CI workspace, never from `build_manifest.json`;
- the child process receives an environment allowlist, not `os.environ.copy()`;
- timeout, `stdin=DEVNULL`, temporary working directory, and output limits are required;
- reports distinguish `STATIC_VERIFIED` from `INTEGRATION_VERIFIED` and `RUNTIME_VERIFIED`;
- documentation must state that temporary-directory isolation is not OS/network sandboxing.

A real sandbox requires an external OS/container boundary and is out of scope for Python-only validation.

## 6. Public/private content boundary

Public by default:

- original scripts, schemas, contracts, neutral templates, synthetic fixtures, and generic workflows;
- redacted examples with clear provenance;
- tests that do not require private sibling trees.

Private or separately reviewed:

- local absolute paths and usernames;
- private cards, novels, project names, and build reports;
- unlicensed third-party IP, copied dialogue, and source-derived examples;
- unpublished experiments and private overlays;
- backups, archives, temporary files, credentials, and request logs.

Every public release must pass both current-tree and export-tree audits. A fresh public history is preferred; historical auditing remains useful for deciding what must not be exported.

## 7. Source audit versus artifact audit

`SOURCE AUDIT` describes the private production tree. It may report private paths, internal cases, archives, or local overlays because those are precisely the materials the exporter must decide about; source findings do not by themselves block a future release.

`ARTIFACT AUDIT` is the release gate. It runs only on the clean export staging tree and is blocking. A Release Candidate requires:

```text
artifact errors = 0
unresolved manual review = 0
unknown provenance = 0
private paths = 0
secrets = 0
broken documentation links = 0
```

The exporter must never bulk-enable unresolved manual review. Each candidate requires a separate review-manifest decision such as `approved_public`, `rejected_private`, or `third_party_reviewed`. A rejected private file remains in the source tree but is absent from the artifact.

## 8. Clean-room evidence

A public candidate must be tested in a clone containing only the exported artifact. Without sibling skills, Core validation must pass at L1, optional native stage routing must report `MISSING`, and the toolchain must not crash. A second environment may add `standalone-card-stage-routing` and verify the explicitly declared L3 capability. Neither environment may claim SillyTavern runtime verification without a real host test.
