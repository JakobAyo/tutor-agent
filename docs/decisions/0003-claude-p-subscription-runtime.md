# 0003: All LLM calls go through `claude -p` on my subscription

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The tutor needs an LLM for two jobs: detecting concepts in agent activity, and teaching them. I already pay for a Claude subscription and don't want separate API billing.

## Decision
- Every LLM call is a headless `claude -p` subprocess.
- Authentication uses a long-lived token from `claude setup-token`. It is stored in `.env` and passed to the subprocess as an environment variable.
- `.env` is git-ignored and is never committed.

## Alternatives considered
- Anthropic API with an API key: finer control (model choice per call, token counts), but it is billed separately from the subscription.
- A local model (Ollama): free and private, but the explanations would be noticeably worse, and explanation quality is the product.

## Consequences
- No API key and no extra cost, but usage counts against the subscription's rate limits, so detection must be batched (see [non-functional requirements](../requirements/non-functional.md)).
- **Recursion risk:** a `claude -p` call started by the tutor would fire my global hooks, and the tutor would then observe itself. Tutor calls must skip the hooks (see [components](../architecture/components.md)).
- Each call pays for a CLI process start-up, so it's slower than a direct API call. That's acceptable because nothing on the agent's critical path waits for it.
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md).
