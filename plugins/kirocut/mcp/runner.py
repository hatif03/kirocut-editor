#!/usr/bin/env python3
"""Runs one long command for the MCP server, on its own, and records how it ended. Standard library only.

    python3 runner.py <job.json>

The job file holds {"cmd": [...], "cwd", "log", "env"?}. The runner starts the command with its output in `log`, writes
{"pid": <the command's pid>, "state": "running"} into the job file, waits, then writes {"state": "done" | "failed" |
"cancelled", "exit": code, "finished": time}. It outlives the MCP server that started it, so a render goes on when
the IDE closes the chat, and the file says how it ended whenever someone looks.

Cancel is `jobs.cancel(job)`: it kills the command's whole process tree and the runner records "cancelled".
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def write(path, patch):
    p = Path(path)
    for _ in range(20):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d.update(patch)
            tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
            os.replace(tmp, p)
            return d
        except (OSError, ValueError):
            time.sleep(0.05)
    return {}


def kill_tree(p):
    """The command and everything it started."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    else:
        import signal
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except OSError:
            p.terminate()


def main(path):
    job = json.loads(Path(path).read_text(encoding="utf-8"))
    env = {**os.environ, **(job.get("env") or {}), "PYTHONUTF8": "1"}
    kw = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000200}   # its own group: a cancel reaches the tree
    with open(job["log"], "ab") as log:
        try:
            p = subprocess.Popen(job["cmd"], cwd=job.get("cwd") or None, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, **kw)
        except OSError as e:
            write(path, {"state": "failed", "exit": None, "error": str(e), "finished": time.time()})
            return 1
        write(path, {"pid": p.pid, "state": "running", "started_run": time.time()})
        killed = False
        while p.poll() is None:   # a cancel is a flag in the job file; this loop is what acts on it
            time.sleep(0.25)
            if not killed:
                try:
                    killed = bool(json.loads(Path(path).read_text(encoding="utf-8")).get("cancel"))
                except (OSError, ValueError):
                    pass
                if killed:
                    kill_tree(p)
        code = p.returncode
    cur = json.loads(Path(path).read_text(encoding="utf-8"))
    state = "cancelled" if cur.get("cancel") else "done" if code == 0 else "failed"
    write(path, {"state": state, "exit": code, "finished": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
