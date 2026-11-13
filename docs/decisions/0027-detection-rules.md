# 0027: How detection results become concepts and notifications

- **Status:** Accepted
- **Date:** 2026-11-13

## Context
M3 turns the structured detection output ([0023](0023-structured-detection-output.md)) into stored concepts and one notification. The M0 draft prompt left open: which categories, how many concepts per batch, what to do when the model claims a concept is known but names it differently, how to check the output, and what a failed call costs.

## Decision
- **Categories** are the eight from the [curriculum](../pedagogy/curriculum.md), as an enum in the schema. The M0 draft's ad-hoc list (`pattern`, `trade-off`, …) is dropped, so the pane can group by the curriculum directly. Trade-offs go into the category of the thing traded.
- **At most 3 concepts per batch**, most valuable first (schema `maxItems` and a cut in code).
- **Known names:** the prompt lists every concept name in the memory, dismissed ones included. The model must reuse a known name exactly and set `reuses_known`.
- **Resolving a candidate** by `concept_id(name)`:
  - unknown id → new concept, status `new`, notified;
  - known id → source attached, no notification;
  - known id but dismissed → nothing stored ([0018](0018-dismissed-status.md));
  - `reuses_known` but no known id matches → dropped and logged. The model saw a known concept and renamed it; storing it would create a near-duplicate.
  - the same id twice in one batch → stored once.
- **Validation** is per item, in code, even though `--json-schema` already validates: empty texts, unknown category, `event_index` out of range or not an integer, non-boolean `reuses_known`. A bad item is logged and dropped, the others are kept. A response without a `concepts` list gives nothing.
- **Snippet:** the content of the event at `event_index`, first 40 lines. The context line is `why_here` ([0013](0013-store-source-snippets.md)).
- **One store transaction per batch** (`ConceptStore.record`), so a batch is stored whole or not at all.
- **A failed call loses the batch.** The reader has already moved the offset. Retrying would mean a second call for the same turn, and later turns usually show the same ideas again.
- **Notification:** one `notify-send` per batch, only for newly created concepts, title "N new concept(s) to learn", one line per concept with its category. Skipped when `muted`. A missing or failing `notify-send` is logged, never raised.
- **Prompt-quality tests** run the real model on the five M0 fixtures under their own pytest marker `prompt`, so `-m real` stays one cheap call.

## Alternatives considered
- Fuzzy-match a renamed known concept to the closest known name: more code, and a wrong match attaches a source to an unrelated concept. Dropping is safe, and the idea comes back in a later turn.
- Drop the whole response if one item is invalid: loses good concepts for one bad index. Each item is independent, so per-item is enough to never half-store a concept.
- Re-read the batch on failure (offset moved only after success): one turn could cost several calls when `claude` is down, against the usage budget.

## Consequences
- The known-names list grows with the memory and is sent on every call. Fine for hundreds of names; if it gets too long, send only names in the matching categories.
- Concepts appear in the pane under the curriculum categories.
- Updated: [architecture/components.md](../architecture/components.md), [observation/triggers.md](../observation/triggers.md), [milestones/m3-detection.md](../milestones/m3-detection.md).
