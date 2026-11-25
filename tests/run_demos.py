#!/usr/bin/env python3
"""Run every script's self-check (tests/demos.txt), on any OS. Standard library only.

    python3 tests/run_demos.py               all of them; keeps going, then lists every failure
    python3 tests/run_demos.py mcp           only the lines that contain "mcp"
    PY=~/.kirocut/venv/bin/python python3 tests/run_demos.py     use the interpreter that holds requirements.lock

CI runs it on each OS (check.yml) and on the newest Python (weekly.yml). It replaces tests/demos.sh, which needed bash:
nothing here does, so Windows runs the same list as Mac and Linux.
"""
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def commands(only=None):
    out = []
    for ln in (ROOT / "tests" / "demos.txt").read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and (not only or only in ln):
            out.append(ln)
    return out


def main(argv):
    py = os.environ.get("PY") or sys.executable
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
    failed = []
    for ln in commands(argv[0] if argv else None):
        parts = shlex.split(ln)
        if parts[0] == "node":
            if not shutil.which("node"):
                print(f"== {ln}\nskipped: node not found")
                continue
            cmd = parts
        else:
            cmd = [py, *parts]
        print(f"== {ln}", flush=True)
        t = time.time()
        r = subprocess.run(cmd, cwd=ROOT, env=env)
        if r.returncode:
            failed.append(ln)
            print(f"-- exit {r.returncode} after {time.time() - t:.0f} s", flush=True)
    if failed:
        print("FAILED:\n  " + "\n  ".join(failed))
        return 1
    print("all demos ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
