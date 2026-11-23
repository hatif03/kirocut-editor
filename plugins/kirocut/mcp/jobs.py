"""Long jobs the tools start (a render, a stills sheet): one detached runner each, a job file, a log. Standard library only.

    start(kind, cmd, cwd, edit=None, out=None) -> job dict       starts runner.py on its own
    get(job_id) -> job dict (state running | done | failed | cancelled, progress, last line)
    cancel(job_id) -> job dict
    list_jobs(limit) -> newest first

A job lives in $KIROCUT_HOME/mcp-jobs/<id>.json and <id>.log. Nothing here holds a process: the runner does, so the job is
the same from any MCP server session, and a finished job stays readable.
"""
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "lib" / "kirocut"
sys.path.insert(0, str(LIB))

PCT = re.compile(r"(\d+)\s*/\s*(\d+)")
PCT_WORD = re.compile(r"(\d{1,3})(?:\.\d+)?\s*%")


def folder():
    f = Path(os.environ.get("KIROCUT_HOME", "").strip() or Path.home() / ".kirocut") / "mcp-jobs"
    f.mkdir(parents=True, exist_ok=True)
    return f


def read(job_id):
    try:
        return json.loads((folder() / f"{job_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def tail(path, n=12, size=8192):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - size))
            lines = f.read().decode("utf-8", "replace").replace("\r", "\n").splitlines()
    except OSError:
        return []
    return [x.rstrip() for x in lines if x.strip()][-n:]


def progress(lines):
    """Percent from the tail of a log: Remotion's 'Rendered 812/3255', or 'NN%' (ffmpeg wrappers). None when it cannot be told."""
    for ln in reversed(lines):
        m = PCT.search(ln)
        if m and int(m.group(2)) > 0 and int(m.group(1)) <= int(m.group(2)):
            return round(100 * int(m.group(1)) / int(m.group(2)))
        m = PCT_WORD.search(ln)
        if m and int(m.group(1)) <= 100:
            return int(m.group(1))
    return None


def start(kind, cmd, cwd=None, edit=None, out=None, env=None):
    import proc
    jid = f"{kind}-{uuid.uuid4().hex[:6]}"
    f = folder()
    job = {"id": jid, "kind": kind, "edit": str(edit) if edit else None, "cmd": [str(c) for c in cmd], "cwd": str(cwd) if cwd else None,
           "log": str(f / f"{jid}.log"), "out": str(out) if out else None, "state": "starting", "started": time.time(),
           "session": os.environ.get("KIROCUT_SESSION", ""), "env": env or {}}
    (f / f"{jid}.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    Path(job["log"]).touch()
    proc.spawn([sys.executable, str(HERE / "runner.py"), str(f / f"{jid}.json")], log=f / f"{jid}.runner.log")
    return view(job)


def view(job):
    """A job as the agent reads it."""
    lines = tail(job["log"])
    out = {"job_id": job["id"], "kind": job["kind"], "state": job["state"], "edit": job.get("edit"), "progress_pct": progress(lines),
           "last_line": lines[-1] if lines else "", "elapsed_s": round((job.get("finished") or time.time()) - job["started"], 1)}
    if job["state"] in ("failed", "cancelled"):
        out["log_tail"] = lines
        out["exit"] = job.get("exit")
        if job.get("error"):
            out["error"] = job["error"]
    if job["state"] == "done" and job.get("out"):
        out["output"] = job["out"] if Path(job["out"]).exists() else None
    return out


def get(job_id):
    job = read(job_id)
    return view(job) if job else None


def cancel(job_id):
    job = read(job_id)
    if not job:
        return None
    if job["state"] in ("starting", "running"):
        p = folder() / f"{job_id}.json"
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d["cancel"] = True
            p.write_text(json.dumps(d, indent=1), encoding="utf-8")
        except (OSError, ValueError):
            pass
        for _ in range(80):   # the runner sees the flag, ends the command's tree and writes "cancelled"
            time.sleep(0.1)
            job = read(job_id)
            if job["state"] not in ("starting", "running"):
                break
    return view(read(job_id))


def list_jobs(limit=10):
    rows = []
    for p in folder().glob("*.json"):
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    rows.sort(key=lambda j: j.get("started", 0), reverse=True)
    return [view(j) for j in rows[:limit]]
