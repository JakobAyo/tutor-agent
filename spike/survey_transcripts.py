"""Spike Q2: survey record types and content-block types across all transcripts.

Usage: python spike/survey_transcripts.py [root]
Prints counts of top-level `type`, assistant/user content-block types, tool names,
and the set of top-level keys per record type. Reads only, prints no content.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / ".claude/projects")
types, blocks, tools, keys, versions = Counter(), Counter(), Counter(), defaultdict(set), Counter()
sidechain = Counter()
bad = 0
for f in root.rglob("*.jsonl"):
    sub = "subagents" in f.parts
    for line in f.open(errors="replace"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        t = r.get("type")
        types[t] += 1
        keys[t].update(r.keys())
        versions[r.get("version")] += 1
        sidechain[(sub, r.get("isSidechain"))] += 1
        msg = r.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("content"), list):
            for b in msg["content"]:
                if isinstance(b, dict):
                    blocks[(t, b.get("type"))] += 1
                    if b.get("type") == "tool_use":
                        tools[b.get("name")] += 1
print("bad lines:", bad)
print("record types:", types.most_common())
print("blocks:", blocks.most_common())
print("tools:", tools.most_common(30))
print("(in subagents dir, isSidechain):", dict(sidechain))
print("versions:", sorted((v for v in versions if v), key=lambda s: [int(x) for x in s.split('.') if x.isdigit()])[::max(1, len(versions)//10)])
for t, k in keys.items():
    print(t, sorted(k))
