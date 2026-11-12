# 0023: Detection returns structured output through `--json-schema`

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The detector must turn an LLM answer into concept records. Parsing JSON out of free text is fragile. The M0 spike found that `claude -p --json-schema <schema>` returns the validated object in a separate `structured_output` field of the `--output-format json` result. All 10 spike calls (Haiku and Sonnet) returned valid objects.

## Decision
- The detection call passes a JSON schema: a list of concepts with `name`, `category`, `summary`, `why_here`, `event_index`, and `reuses_known`.
- The detector reads `structured_output` and never parses `result`.
- `event_index` points into the batch, so the detector can attach the source snippet itself ([0013](0013-store-source-snippets.md)) instead of asking the model to copy code.

## Alternatives considered
- Ask for JSON in the prompt and parse `result`: works most of the time, and fails silently otherwise.

## Consequences
- No parsing code and no retry-on-bad-JSON logic.
- The schema lives in code and is versioned with the prompt.
- Updated: [architecture/components.md](../architecture/components.md).
