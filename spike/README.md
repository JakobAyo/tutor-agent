# M0 spike (throwaway)

Small scripts that answered the questions in [docs/milestones/m0-spike.md](../docs/milestones/m0-spike.md). Not part of the package. Don't import from here; the real code is built in M1+.

| Script | Question | What it does |
|---|---|---|
| `survey_transcripts.py` | Q2 | Counts record and block types across all local transcripts |
| `extract_events.py` | Q2 | Draft JSONL → event mapping and turn splitting |
| `dump_hook.py` | Q1 | Hook that logs its stdin payload |
| `sandbox_test.sh` | Q3, Q4 | Compares `claude -p` flag sets (hooks fired, `CLAUDE.md` leak, tools) |
| `detach_hook.py`, `detached_worker.py` | Q4–Q6 | Hook that starts a detached `claude -p`, plus the env-var guard |
| `make_fixtures.py` | Q7 | Cuts transcript turns into anonymized batches in `tests/fixtures/batches/` |
| `detect.py` | Q7, Q8 | Draft detection prompt and schema, one call per batch and model |
| `lesson.py` | Q8 | Times one lesson call |
| `clean_env.sh` | – | Strips the surrounding Claude Code session's env vars before nested runs |

`results/` holds the captured evidence (anonymized hook payloads, detection outputs).

Hook tests used a project-local `.claude/settings.json` in a scratch directory. The global settings were never changed.
