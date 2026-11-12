# Teaching Triggers

> **Responsibility:** Which observed events trigger a teaching moment, and how they're filtered.

## When detection runs
- **Automatic:** once per finished agent turn (the hook fires) on the new transcript events ([0007](../decisions/0007-interaction-model.md)).
- **Pre-filter (no LLM call):** skip the turn if it contains no code edits, no commands, and no substantial reasoning.
- **On demand:** from the tutor pane ("explain what just happened").

## The "worth knowing" filter
A concept triggers a notification only if **both** are true:

1. **New to me:** it is not in the concept memory with any status, and it hasn't been dismissed.
2. **Reusable understanding:** knowing it will help me understand *future* code, not just this line. For example:
   - **Yes:** design patterns (repository, dependency injection), architecture (event sourcing, CQRS), concurrency models, testing strategies (mocking vs fakes), tooling internals (how lockfiles work), infra concepts (connection pooling, migrations), language mechanisms (Python decorators, TS generics, Rust ownership), trade-offs (why a queue instead of a direct call).
   - **No:** basic syntax (`for` loops, `if`, assignment), single API calls with no idea behind them, trivial renames and formatting.

## Concept identity
- Concepts are named at a general level ("dependency injection", not "the `get_db` function").
- The detector receives the list of known concept names, so it reuses an existing name instead of creating a near-duplicate.
