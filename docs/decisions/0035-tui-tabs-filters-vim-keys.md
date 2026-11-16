# 0035: Tutor pane: status tabs, filters, and vim keys

- **Status:** Accepted
- **Date:** 2026-11-16

## Context
The tutor pane ([0028](0028-lessons-and-tutor-pane.md)) shows one long list grouped by status, `new` first. After a few days of use it holds dozens of concepts. Read concepts pile up below the new ones, there is no way to narrow the list to one project or category, and finding a concept by name means scrolling. Navigation uses arrow keys only, while I work in vim-style tools all day.

## Decision
- **Status tabs** above the list: `New · Seen · Understood · Dismissed · All`, each with its count. Only the active tab's concepts are listed. The pane always opens on `New`. `All` lists every status, dismissed included. Tabs switch with `1`–`5` or `[` / `]`. The Dismissed tab replaces the `h` toggle from [0028](0028-lessons-and-tutor-pane.md).
- **Status icons and colour** on each row: `●` new, `◐` seen, `✓` understood, `✗` dismissed. A status change moves the concept out of the current tab (unless it is `All`). A toast names the change, and `z` undoes the last status change made in this pane.
- **Search:** `/` opens a search line above the list. Matching is a case-insensitive fuzzy match (the letters in order) on the name, or a substring match on the summary, and the list narrows as I type. Enter keeps the filter and returns to the list. Esc in the search line clears it.
- **Filters:** `p` picks a project and `c` picks a category, each from a small picker built from the concepts in memory (with an "any" entry). `o` cycles the sort: newest, oldest, most often seen, A–Z. Filters and sort apply to every tab, and tab counts reflect the filters.
- **Filter chips line** above the list shows the active search, project, category, and sort. Esc on the list clears all filters.
- **Vim motions:** `j` / `k` move, `g` / `G` jump to the top and bottom, `h` / `l` move focus between the list and the lesson, `Ctrl-d` / `Ctrl-u` scroll the lesson half a page. Arrow keys keep working.
- **Reading space:** `m` hides the list so the lesson (and its follow-up input) uses the full width. `m` again brings it back.
- **Help:** `?` opens an overlay that lists every key, grouped by navigation, filters, status, and lessons. The footer shows only the most used keys.
- **Unchanged:** `Enter`, `u`, `s`, `d`, `n`, `r`, `f`, `w`, `x`, `q`, the lesson pane, follow-ups, explanations, and the polling reload. The default Textual theme stays. Nothing is saved between launches.
- **Code:** filtering, matching, sorting, and counting are pure functions in their own module (`browse.py`), tested without Textual. `tui.py` only wires them to widgets. No new dependency.

## Alternatives considered
- Collapsible status groups: less change, but the list still grows with every read concept, and folding adds keys of its own.
- A tree by category or project: good for browsing, but status is what I act on most, and the project and category filters cover the rest.
- A sortable table: dense, but the columns don't fit in a side pane next to the lesson.
- A leader key (`Space u`, `Space f`): frees every letter for motions, but doubles the keystrokes for the actions I use most. Only `h` clashed, and the tabs make it unnecessary.
- Remembering the tab, filters, and sort between launches: opening on `New` with no filters is predictable and shows what needs attention.
- A fuzzy-matching library (`rapidfuzz`): better ranking, but a dependency for a list of a few hundred names.
- Animations: not wanted. Textual's default scrolling is enough.

## Consequences
- Read concepts no longer crowd the view. `New` is the inbox and the other tabs are the archive.
- More keys to learn. The `?` overlay and the chips line keep them discoverable.
- `h` changes meaning (focus left instead of "show dismissed").
- The README screenshot (`docs/assets/tutor-pane.svg`) must be regenerated once the pane is built.
- Updated: [requirements/functional.md](../requirements/functional.md) (F5, F11), [pedagogy/learner-model.md](../pedagogy/learner-model.md), [architecture/components.md](../architecture/components.md), [milestones/overview.md](../milestones/overview.md), [milestones/m6-daily-use.md](../milestones/m6-daily-use.md), `README.md`, `CLAUDE.md`. [0028](0028-lessons-and-tutor-pane.md) is partly superseded (the `h` key and the grouped list).
