# 0016: Detection uses a cheaper model than lessons

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Every LLM call goes through `claude -p` on the subscription ([0003](0003-claude-p-subscription-runtime.md)), so usage is limited. Detection runs after every agent turn and is a fairly simple extraction and classification job. Lessons and follow-ups run rarely, and explanation quality is the product.

## Decision
- The Claude runner takes a model per call (`claude -p --model ...`).
- **Detection** uses a cheaper, faster model (Haiku class).
- **Lessons and follow-ups** use a stronger model (Sonnet or Opus class).
- Both model names are settings, not hard-coded.

## Alternatives considered
- One default model for everything: simpler, but detection would use far more of the subscription's usage than it needs.

## Consequences
- Detection costs less usage and runs faster.
- A cheaper model may miss concepts or misjudge "worth knowing". Check detection quality on real transcripts in the spike, and switch the detection model if needed.
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md), [architecture/components.md](../architecture/components.md).
