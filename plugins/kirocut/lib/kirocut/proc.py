#!/usr/bin/env python3
"""Start a process that outlives the program that started it, on every OS. Stdlib only.

The editor's window and its review pages are servers the chat starts and then forgets. They must keep running when
the MCP server (or the terminal) that started them goes away, and must not pop a console window on Windows.

    spawn(cmd, cwd=None, env=None, log=None) -> Popen
    python3 proc.py demo
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Windows creation flags: no console window, own process group, and out of the parent's job object when allowed
# (an IDE often runs its tools in a job that kills its children when it closes).
DETACHED = 0x00000008
NEW_GROUP = 0x00000200
NO_WINDOW = 0x08000000
BREAKAWAY = 0x01000000


def spawn(cmd, cwd=None, env=None, log=None):
    """cmd (a list) running on its own: stdin closed, output to `log` (a file path) or nowhere."""
    out = open(log, "ab") if log else subprocess.DEVNULL
    kw = dict(cwd=str(cwd) if cwd else None, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT if log else subprocess.DEVNULL)
    try:
        if os.name == "nt":
            try:
                return subprocess.Popen(cmd, creationflags=DETACHED | NEW_GROUP | NO_WINDOW | BREAKAWAY, close_fds=True, **kw)
            except OSError:   # the job does not allow breakaway
                return subprocess.Popen(cmd, creationflags=DETACHED | NEW_GROUP | NO_WINDOW, close_fds=True, **kw)
        return subprocess.Popen(cmd, start_new_session=True, close_fds=True, **kw)
    finally:
        if log:
            out.close()


def demo():
    tmp = Path(tempfile.mkdtemp(prefix="proc_demo_"))
    marker = tmp / "ran.txt"
    p = spawn([sys.executable, "-c", f"import time; time.sleep(0.3); open({str(marker)!r}, 'w').write('x')"], log=tmp / "log.txt")
    assert p.poll() is None, "it runs on its own, we do not wait for it"
    for _ in range(50):
        if marker.exists():
            break
        time.sleep(0.1)
    assert marker.exists(), "the child ran to the end"
    p.wait(timeout=5)
    print("proc demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
