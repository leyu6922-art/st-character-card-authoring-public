# Structured card run-validation checklist

> This is a reusable validation method, not a transcript. Use only a self-authored or authorized test fixture; do not commit novel excerpts, private card exports, or personal logs.

## Purpose

Static validators prove that a card is well-formed. A short controlled run checks whether the same contracts remain understandable when the card is actually used. The run should test one bounded scenario and record observations without copying private conversation content into the repository.

## Neutral scenario

Use a four-round information-exchange or item-selection scene with:

- one player-controlled decision per round;
- one NPC with a stable identity and a bounded refusal/escalation policy;
- one state field that changes only after an observable event;
- one optional structured output block that can be hidden from the player;
- no automatic movement, consent, secret reveal, or phase transition.

## Assertions by round

### Round 1 — cold start

- The current route and scene are identified.
- The NPC responds from its profile rather than inventing unrelated history.
- The player receives a meaningful choice instead of an automatic result.
- Any structured block follows the documented syntax and is not mistaken for prose.

### Rounds 2–3 — continuity

- The NPC keeps its vocabulary, attitude, and refusal threshold.
- State changes have a visible cause and do not jump without evidence.
- A cheaper or safer alternative is offered only when the card specifies one.
- The model does not reveal hidden information merely because it exists in the full card.

### Round 4 — boundary check

- The scene can end, pause, or branch without forced escalation.
- The player still owns movement, consent, internal reactions, and final decisions.
- The output remains within the selected phase and does not load unrelated modules.
- The report records failures by contract, not by subjective prose preference.

## Record format

Keep the report to a table of assertions, observed status, and a short evidence pointer. Store the test fixture outside the public repository when it contains copyrighted, private, or adult source material. The public repository should contain only the checklist and synthetic fixtures.

## Failure taxonomy

| Code | Meaning | Typical fix |
|---|---|---|
| `ROUTE_DRIFT` | The response leaves the current route without a trigger | tighten route keys and transition conditions |
| `PROFILE_DRIFT` | NPC vocabulary or behavior contradicts its profile | add a concrete behavior anchor |
| `STATE_JUMP` | A value changes without an observable cause | classify ownership and write-back evidence |
| `PLAYER_TAKEOVER` | The model decides or acts for the player | restore the handoff point |
| `SECRET_LEAK` | Hidden facts appear without a player trigger | separate knowledge scopes and secret policy |
| `FORMAT_DRIFT` | Structured output breaks its documented syntax | repair the output contract and parser test |

This method complements static gates and does not claim to replace real SillyTavern runtime testing.
