"""What `tutor detect` does with one transcript: read the new batch, pre-filter, detect, store,
notify.

Runs detached from the hook, so every failure is logged here and nowhere else.
"""

from pathlib import Path

from tutor_agent import detector, events, notifier, prefilter, reader, settings
from tutor_agent.log import get_logger
from tutor_agent.store import Concept, ConceptStore, Entry, Outcome, Source, concept_id


def process(transcript: Path, session_id: str | None, *, dry_run: bool) -> int:
    log = get_logger()
    try:
        # Claude Code runs internal helper agents after a turn: they fire `SubagentStop` but never
        # write a transcript. Not an error, so no traceback. A missing main transcript still is.
        if transcript.parent.name == "subagents" and not transcript.exists():
            log.info("skip %s: no transcript (internal agent)", transcript.name)
            return 0
        batch = reader.read_new(transcript, session_id, advance=not dry_run)
        where = f"{batch.transcript.name} lines {batch.first_line}-{batch.last_line}"
        reason = prefilter.skip_reason(batch.events)
        if reason:
            log.info("skip %s: %s", where, reason)
            return 0
        if dry_run:
            log.info("dry run %s, %d events:\n%s", where, len(batch.events), events.to_json(batch.events))
            return 0
        detect_and_store(batch, where)
        return 0
    except Exception:
        log.exception("detect failed for %s", transcript)
        return 1


def detect_and_store(batch: reader.Batch, where: str) -> list[Concept]:
    """One detection call, one store transaction, at most one notification. Returns new concepts.

    The offset has already moved, so a failed call loses this batch. That is on purpose: retrying
    would mean a second call for the same turn, and the next turn usually shows the same ideas.
    """
    log = get_logger()
    cfg = settings.load()
    store = ConceptStore()
    known = {c.id: c for c in store.list()}  # every status, dismissed included (ADR 0018)
    candidates = detector.detect(batch.events, [c.name for c in known.values()], cfg)

    entries: list[Entry] = []
    for cand in candidates:
        cid = concept_id(cand.name)
        if cand.reuses_known and cid not in known:
            # The model says "known" but renamed it: storing it would make a near-duplicate.
            log.info("drop %r: marked known but matches no known name", cand.name)
            continue
        if any(concept_id(e.name) == cid for e in entries):
            continue
        ev = cand.event
        entries.append(Entry(cand.name, cand.category, cand.summary, Source(
            snippet=detector.snippet(ev), context=cand.why_here, project=ev.project or None,
            session_id=batch.session_id, transcript_ref=ev.transcript_ref, file=ev.file,
        )))

    results = store.record(entries)
    new = [c for c, outcome in results if outcome is Outcome.CREATED]
    log.info("detected %s: %s", where, ", ".join(f"{c.name} [{o}]" for c, o in results) or "nothing")
    notifier.notify(new, muted=cfg.muted)
    return new
