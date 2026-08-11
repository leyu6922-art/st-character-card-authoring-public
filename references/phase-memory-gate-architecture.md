# Phase Memory Gate Architecture

> Status: active contract draft for native title-routed stage cards.

## Purpose

A stage-routed card may contain a complete character arc while the current route only exposes facts that have actually happened. The phase-memory gate separates long-horizon causal understanding from current narrative memory.

## Three-layer model

### 1. Full causal archive

A constant, non-triggered entry may describe the character's stable personality, long-term causal direction, continuity anchors, and irreversible points. It explains the arc; it does not make future events current facts.

### 2. Phase memory gate

A constant protocol entry states that when the current route is `P#`, only events, relationships, and secrets from the start through `P#` are available as established memory. Future-stage material is only a candidate direction. Current route state wins when information conflicts.

### 3. Compact system prompt anchor

The production validator checks a compact anchor in `data.system_prompt`. It must contain the exact markers:

```text
阶段表演规则
仅记得
```

The current production contract also requires the configured minimum length (40 characters by default). The compact anchor is a reachability signal; detailed semantics belong in the causal archive and memory-gate entries.

## Routing boundary

This contract applies to native Greeting-title routing. `ROUTE_STAGE=P#` / Author's Note routing is an external preset route and is not a production-supported native route unless a separate adapter explicitly declares it.

## Verification

The shared implementation is:

```text
scripts/lib/stage_memory.py
```

Its regression fixtures are in:

```text
tests/test_stage_memory_gate.py
```

A delivery project must also satisfy the stage-entry contract and the four stage material packs required by its declared native routing profile. Static validation does not claim SillyTavern runtime verification.

## Evidence boundary

- `SPECIFIED`: this document and the stage-entry contract define the rule.
- `STATIC_VERIFIED`: validator checks the anchor and route structure.
- `INTEGRATION_VERIFIED`: build and delivery checks prove source/manifest/card alignment.
- `RUNTIME_VERIFIED`: only a real SillyTavern host test may claim runtime behavior.
