# Public Core Release Boundary

## Purpose

This candidate is a sanitized public Core, not a mirror of the private production tree.

```text
private production source
        |
        | explicit allowlist + reviewed overrides
        v
clean public artifact
```

## Included boundary

Only newly authored public-readiness contracts, tools, tests, and neutral documentation are included. Private cases, source novels, images, presets, archived material, local paths, and sibling skills stay outside the artifact.

## Release gates

```text
pytest                    PASS
pipeline/static checks    PASS when bundled
artifact audit            PASS
manual review unresolved  0
provenance unresolved     0
private paths             0
secrets                   0
license                   present and reviewed
```

The source tree may contain private material. The artifact must not.

## Evidence levels

`SPECIFIED` is a written contract. `STATIC_VERIFIED` is a deterministic local check. `INTEGRATION_VERIFIED` requires explicit trusted builder execution. `RUNTIME_VERIFIED` requires a real SillyTavern host. `OBSERVED` records human observation.

A passing static audit never implies runtime verification.
