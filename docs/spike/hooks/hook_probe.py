#!/usr/bin/env python3
"""The command behind the spike hooks. Reads the hook event JSON on stdin and answers per mode.

    prompt   prints a marker line; if the agent repeats SPIKE-HOOK-OK-<time> the stdout reached it
    block    exits 2 with a reason on stderr (blocks a PreToolUse); the agent should see the reason
    stop     appends the event to stop.log beside this file
"""
import json
import sys
import time
from pathlib import Path

mode = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    event = json.loads(sys.stdin.read() or "{}")
except ValueError:
    event = {}
here = Path(__file__).resolve().parent

if mode == "prompt":
    print(f"SPIKE-HOOK-OK-{time.strftime('%H%M%S')}: tell the user this marker text so we know hook output reaches you.")
elif mode == "block":
    sys.stderr.write("SPIKE-BLOCKED: the PreToolUse hook blocked this tool on purpose.")
    sys.exit(2)
elif mode == "stop":
    with open(here / "stop.log", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%H:%M:%S"), "event": event})[:600] + "\n")
