"""What the user did in the editor window, for the chat to pick up. Standard library only.

The window and the review pages already keep their own persisted queues, each with an exactly-once take:

    home window   state.json jobs ("queued" until a session takes one)           home.take_next(session)
    review page   review.json events (send, approve, edits) and the learn and     review.pending(edit), review.report(edit)
                  trial-reel steps, each "handled" once taken

This module is the one view over both for the MCP server: `scan` says what is waiting, `take` takes it,
`poll` waits for it and keeps the pages' "Kiro is listening" light on while it does.

The session is this server's own id (KIROCUT_SESSION). A job a session takes is owned by it, so the page's
Stop and the cancel lines reach the right chat.
"""
import contextlib
import io
import json
import os
import time
import uuid
from pathlib import Path

SESSION = os.environ.setdefault("KIROCUT_SESSION", "kiro-" + uuid.uuid4().hex[:12])


def _edit_dirs():
    import library
    try:
        return [Path(d) for d in library.edit_dirs()]
    except OSError:
        return []


def _reviews():
    """Edit folders that have a review page (review.json)."""
    return [d for d in _edit_dirs() if (d / "review.json").is_file()]


def scan():
    """What is waiting now, without taking it: {"jobs": n, "reviews": [edit folders with a send, approve or step waiting]}."""
    import home
    import review
    out = {"jobs": 0, "reviews": []}
    try:
        d = home.read()
        out["jobs"] = sum(1 for j in d["jobs"] if home.takeable(j, SESSION, d) or (j.get("cancel") and not j.get("cancel_sent")))
    except Exception:   # noqa: BLE001  no window state yet
        pass
    out["reviews"] = [str(f) for f in _reviews() if review.pending(f)]
    return out


def pending_count():
    s = scan()
    return s["jobs"] + len(s["reviews"])


def beat(on=True):
    """The pages' 'Kiro is listening' light: the home window's .listening, and each served edit's review/.listening."""
    import home
    import review
    hb = home.home() / ".listening"
    if not on:
        hb.unlink(missing_ok=True)
        for f in _reviews():
            b = f / "review" / ".listening"
            try:
                if json.loads(b.read_text(encoding="utf-8")).get("session") == SESSION:
                    b.unlink(missing_ok=True)
            except (OSError, ValueError):
                pass
        return
    hb.parent.mkdir(parents=True, exist_ok=True)
    hb.write_text(SESSION, encoding="utf-8")
    me = {"pid": os.getpid(), "session": SESSION, "kind": "kiro", "since": time.time()}
    for f in _reviews():
        if (f / "review" / ".server").exists():
            b = f / "review" / ".listening"
            try:
                b.write_text(json.dumps(me), encoding="utf-8")
            except OSError:
                pass


def take():
    """Take everything waiting. A list of {"kind": "job" | "review", ...}."""
    import home
    import review
    got = []
    while True:   # a session takes one video at a time: keep asking until nothing more is takeable
        line = home.take_next(SESSION)
        if line is None:
            break
        got.append({"kind": "job", "line": line, "type": line.split()[1] if line.split()[1:] else ""})
        if len(got) > 20:
            break
    for f in _reviews():
        if review.pending(f):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                typ = review.report(f)
            got.append({"kind": "review", "edit": f.name, "folder": str(f), "type": typ if isinstance(typ, str) else str(typ),
                        "text": buf.getvalue().strip()})
    return got


def poll(wait_s, ctx=None, every=1.0, beat_s=5.0):
    """Wait up to wait_s seconds for something to take; take it and return it. [] when the time ran out."""
    end, last, n = time.time() + max(0.0, wait_s), 0.0, 0
    try:
        while True:
            now = time.time()
            if now - last >= beat_s or last == 0.0:
                beat(True)
                if last:
                    n += 1
                    if ctx is not None:
                        ctx.progress(n, None, "Waiting for the editor window")
                last = now
            s = scan()
            if s["jobs"] or s["reviews"]:
                got = take()
                if got:
                    return got
            if now >= end or (ctx is not None and ctx.cancelled.is_set()):
                return []
            time.sleep(every)
    finally:
        beat(False)
