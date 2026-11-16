"""Render the README screenshot of the tutor pane from demo data. Makes no model call.

    uv run python scripts/readme_screenshot.py

Seeds a throwaway data directory with made-up concepts and one cached lesson, opens that
lesson headless, and saves `docs/assets/tutor-pane.svg`. Nothing from your real concept
memory is read or shown.
"""

import asyncio
import os
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs/assets/tutor-pane.svg"
PROJECT = "/home/u/Projects/shop-api"

CONCEPTS = [
    (
        "Advisory file locking",
        "Concurrency",
        "Processes agree to take a lock file before touching shared state; the OS does not "
        "enforce it.",
        "with open(lock, 'w') as f:\n    fcntl.flock(f, fcntl.LOCK_EX)\n    store.save(data)",
        "The agent wrapped the JSON store write in an exclusive flock.",
    ),
    (
        "Idempotency keys",
        "API design",
        "A client-chosen key makes a retried POST safe: the server returns the first result.",
        "key = request.headers['Idempotency-Key']",
        "Payment endpoint dedupes retries by key.",
    ),
    (
        "Atomic rename for safe writes",
        "Reliability",
        "Write to a temp file, fsync, then rename over the target so readers never see half.",
        "os.replace(tmp, path)",
        "Store writes go through a temp file.",
    ),
    (
        "Exponential backoff with jitter",
        "Reliability",
        "Retry delays grow geometrically, randomized so clients do not retry in lockstep.",
        "delay = base * 2**attempt * random.random()",
        "HTTP client retries on 429.",
    ),
    (
        "Dependency injection",
        "Design patterns",
        "Pass collaborators in instead of constructing them, so tests can swap fakes.",
        "def __init__(self, store: Store | None = None):",
        "The app takes its store as a parameter.",
    ),
    (
        "Cursor-based pagination",
        "API design",
        "Page with an opaque pointer to the last row instead of an offset.",
        "WHERE id > :cursor ORDER BY id LIMIT 50",
        "Orders list endpoint.",
    ),
    (
        "Optimistic concurrency control",
        "Databases",
        "Detect conflicting updates with a version column instead of holding locks.",
        "UPDATE orders SET ..., version = version + 1 WHERE id = :id AND version = :v",
        "Order update checks the row version.",
    ),
]

LESSON = """\
**Where it showed up.** In `shop-api`, the agent made two processes write the same
`orders.json`: the web worker and a cron job. It wrapped the write like this:

```python
with open(lock_path, "w") as f:
    fcntl.flock(f, fcntl.LOCK_EX)   # waits for the lock
    store.save(orders)
```

**Why.** Without the lock, both processes can read the old file, change it, and write it back.
The second write silently drops the first one's changes (a *lost update*).

**The idea.** `flock` is *advisory*: the kernel only tracks who holds the lock. It does not stop
a process that never asks for it. It works because every writer agrees to take it first.

**Trade-offs.**
- Cheap and simple, and the lock is released when the process dies.
- Only protects cooperating code. Not reliable on NFS.
- For more writers, a real database is the next step.

**Further reading:** `man 2 flock`, *Designing Data-Intensive Applications*, ch. 7.
"""


async def shoot() -> None:
    # Imported here, after TUTOR_AGENT_DATA_DIR points at the throwaway directory.
    from tutor_agent import lessons  # noqa: PLC0415
    from tutor_agent.settings import Settings  # noqa: PLC0415
    from tutor_agent.store import ConceptStore, Entry, Source, Status  # noqa: PLC0415
    from tutor_agent.tui import TutorApp  # noqa: PLC0415

    store = ConceptStore()
    for name, category, summary, snippet, context in reversed(CONCEPTS):
        source = Source(snippet=snippet, context=context, project=PROJECT, kind="edit")
        store.record([Entry(name, category, summary, source)])
    for cid in ("dependency-injection", "exponential-backoff-with-jitter"):
        store.set_status(cid, Status.UNDERSTOOD)
    store.set_status("cursor-based-pagination", Status.SEEN)
    # Left `new`: Enter opens it from the New tab, and it stays listed there (ADR 0035).

    lock = store.get("advisory-file-locking")
    if lock is None:
        raise SystemExit("demo concept was not stored")
    lessons.LessonCache().put(
        lessons.Lesson(lock.id, LESSON, "sonnet", lock.created_at, lock.sources[-1])
    )

    app = TutorApp(store=store, cfg=Settings(), poll_s=60)
    async with app.run_test(size=(130, 36)) as pilot:
        await pilot.pause()
        app.highlight(lock.id)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause(0.5)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        app.save_screenshot(filename=OUT.name, path=str(OUT.parent))
    print(f"wrote {OUT}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TUTOR_AGENT_DATA_DIR"] = tmp
        asyncio.run(shoot())


if __name__ == "__main__":
    main()
