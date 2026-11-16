# 0028: Lesson format, lesson cache files, and tutor pane behaviour

- **Status:** Accepted
- **Date:** 2026-11-13

## Context
M4 builds the tutor pane and lessons. [0017](0017-lesson-cache.md) says lessons are cached per concept, but not in what form. [0009](0009-textual-tui.md) picks Textual, but not how the pane notices new concepts or when it spends an LLM call. Follow-ups in M5 need the lesson and the source it was built from ([0012](0012-stateless-follow-ups.md)).

## Decision
- **Lesson call:** one plain-text `claude -p` call on `lesson_model` (no `--json-schema`). The prompt holds the concept's name, category, summary, and the **most recent source** (project, file, context, snippet). The snippet sits in a backtick fence longer than any run inside it. The system prompt fixes five Markdown sections in the [teaching-strategy](../pedagogy/teaching-strategy.md) order, at most 500 words, and 2–3 links it is confident exist.
- **Lesson cache:** `lessons/<concept_id>.json` in the data directory, one file per concept, with `text`, `model`, `generated_at`, and a copy of the **source** the lesson was built from. Written to a temp file and swapped in with `os.replace`. A file that can't be parsed counts as missing and is replaced on the next open. Only the pane writes it, so there is no lock.
- **When the pane calls the model:** highlighting a concept shows its cached lesson, or a card (summary, context, "press Enter") if there is none. It never makes a call. **Enter** opens the lesson: `new` becomes `seen`, and the lesson is generated if it isn't cached. **r** regenerates it.
- **Responsiveness:** the call runs in a Textual worker thread. The lesson area shows a loading state, and the list and keys keep working. A failed call is logged and shown under the card, and nothing is cached.
- **New concepts:** the pane checks the concept file's mtime and size once a second and reloads when they change. Readers never take the store lock, so the detector is never slowed down.
- **Status keys** follow the [learner model](../pedagogy/learner-model.md): `u` understood (from `new`/`seen`), `s` back to `seen` (from `understood`), `d` dismiss (from any), `n` undo a dismissal (to `new`), `h` show or hide dismissed concepts. Any other combination shows a warning and changes nothing.

## Alternatives considered
- Generate on highlight: browsing the list would spend a strong-model call per concept passed.
- Cache plain Markdown files: simpler, but M5 follow-ups would have no record of which snippet the lesson quoted.
- A file watcher (`watchfiles`, inotify): instant, but adds a dependency. A one-second poll of one `stat` call is enough for a human-paced pane.
- Structured lesson output (`--json-schema` with one field per section): easier to check, but Markdown is what the pane renders, and the model writes it well without a schema.

## Consequences
- Browsing is free. Only Enter (first time) and `r` cost usage.
- Links come from the model's memory, with no tools to check them. They can be wrong. Watch for this in M6.
- A lesson is only as good as its snippet. When the snippet is chat text, the lesson quotes chat text (see the M6 log).
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/components.md](../architecture/components.md), [architecture/tech-stack.md](../architecture/tech-stack.md).
