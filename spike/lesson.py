"""Spike Q8: time one lesson call. Usage: python spike/lesson.py <batch.json> <event_index> <concept> <model>"""
import json, os, subprocess, sys, time
from pathlib import Path
batch = json.loads(Path(sys.argv[1]).read_text())
ev, concept, model = batch[int(sys.argv[2])], sys.argv[3], sys.argv[4]
system = ("You are a tutor. The learner has a CS degree but little practical experience. "
          "Explain the concept starting from the real code below, then generalize, then give 2-3 links "
          "for further reading. Explain why the agent did it. Keep it under 400 words. Skip basics.")
prompt = f"CONCEPT: {concept}\n\nCODE WHERE IT APPEARED ({ev['kind']} {ev.get('file') or ''}):\n{ev['content']}"
d = Path.home() / ".local/share/tutor-agent-spike"
t0 = time.perf_counter()
p = subprocess.run(["claude", "-p", "--model", model, "--output-format", "json", "--tools", "", "--setting-sources", "",
                    "--strict-mcp-config", "--no-session-persistence", "--system-prompt", system],
                   input=prompt, capture_output=True, text=True, cwd=d, env={**os.environ, "TUTOR_AGENT_INTERNAL": "1"})
r = json.loads(p.stdout)
print(f"{model}: {(time.perf_counter()-t0):.1f}s, ttft {r.get('ttft_ms')} ms, out {r['usage']['output_tokens']} tok, ${r['total_cost_usd']:.4f}")
print(r["result"][:700], "...\n")
