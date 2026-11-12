# 0017: Lessons are cached per concept and regenerated only on request

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Lessons use the stronger model ([0016](0016-model-per-job.md)). Each call takes several seconds and costs subscription usage, and I'll often reopen the same lesson. Follow-up questions also need the lesson text as context ([0012](0012-stateless-follow-ups.md)), so it has to be stored somewhere anyway.

## Decision
- The first time I open a concept, its lesson is generated and saved in a **lesson cache** in the tutor data directory, one entry per concept.
- Reopening the lesson shows the cached text without an LLM call.
- A lesson is regenerated **only when I ask for it** (a "regenerate" key in the tutor pane). New source references don't invalidate the cache.

## Alternatives considered
- No cache: simpler, but slow and wasteful, and follow-ups would have no stable lesson text to refer to.
- Regenerate automatically when a new source is added: lessons stay current, but it needs staleness rules and spends usage on lessons I may never reopen.

## Consequences
- Reopening is instant and free.
- A cached lesson may quote an older snippet than the most recent source. That's fine because the older snippet is still real code ([0013](0013-store-source-snippets.md)).
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/components.md](../architecture/components.md).
