#!/usr/bin/env python3
"""Moves an older install's files to today's names, once. Standard library only.

Edits and the window's state made before KiroCut ran in the Kiro chat used another agent's name for a few files and
keys. This is the only module that knows those names: everything else reads today's.

    edit(folder)        <edit>/review/.<old> -> .kiro, review/<old>*.json -> agent*.json, review.json's <old> key -> "agent",
                        trial-reel kinds <old> -> "kiro", scene items by <old> -> "kiro"
    state(d)            the window's state.json: <old>_seen / <old>_v -> agent_seen / agent_v, a job's <old> key dropped
    python3 legacy.py demo

Every function is safe to call any number of times and never raises: a file it cannot move stays where it is.
"""
import json
import os
import sys
from pathlib import Path

OLD = "cl" + "aude"   # spelled apart so a search for the old agent's name finds this one module only
_DONE = set()


def _jload(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _jsave(p, d):
    tmp = Path(p).with_name(f".{Path(p).name}.{os.getpid()}.legacy")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _by(x):
    """Scene items marked by the old agent are marked by Kiro. True when it changed anything."""
    hit = False
    if isinstance(x, dict):
        if x.get("by") == OLD:
            x["by"], hit = "kiro", True
        for v in x.values():
            hit = _by(v) or hit
    elif isinstance(x, list):
        for v in x:
            hit = _by(v) or hit
    return hit


def review_doc(d):
    """review.json's old keys, in place. True when it changed."""
    if not isinstance(d, dict):
        return False
    hit = False
    if OLD in d:
        old = d.pop(OLD) or {}
        d["agent"] = {**old, **(d.get("agent") or {})}
        hit = True
    tr = d.get("trials")
    for v in (tr or {}).get("versions") or [] if isinstance(tr, dict) else []:
        if isinstance(v, dict) and (v.get("kinds") == OLD or v.get("kinds") == [OLD]):
            v["kinds"], hit = ["kiro"], True
    return hit


def edit(folder):
    """One edit folder's files and keys, moved to today's names. Once per folder per process."""
    f = Path(folder)
    key = str(f.resolve()) if f.exists() else str(f)
    if key in _DONE:
        return
    _DONE.add(key)
    r = f / "review"
    try:
        old_mark = r / ("." + OLD)
        if old_mark.exists():
            if (r / ".kiro").exists():
                old_mark.unlink()
            else:
                old_mark.replace(r / ".kiro")
        for p in sorted(r.glob(OLD + "*.json")) if r.is_dir() else []:
            new = p.with_name("agent" + p.name[len(OLD):])
            if new.exists():
                p.unlink()
            else:
                p.replace(new)
    except OSError:
        pass
    rj = f / "review.json"
    d = _jload(rj)
    if d is not None and review_doc(d):
        try:
            _jsave(rj, d)
        except OSError:
            pass
    for sc in f.glob("scene*.json") if f.is_dir() else []:
        s = _jload(sc)
        if s is not None and _by(s):
            try:
                _jsave(sc, s)
            except OSError:
                pass


def state(d):
    """The window's state.json, in place. True when it changed."""
    if not isinstance(d, dict):
        return False
    hit = False
    for k in ("seen", "v"):
        if f"{OLD}_{k}" in d:
            d.setdefault(f"agent_{k}", d.pop(f"{OLD}_{k}"))
            hit = True
    for j in d.get("jobs") or []:
        if isinstance(j, dict) and OLD in j:
            j.pop(OLD)
            j.pop("reserved", None)
            hit = True
    return hit


def demo():
    import tempfile
    t = Path(tempfile.mkdtemp(prefix="legacy_demo_"))
    e = t / "edits" / "old"
    (e / "review").mkdir(parents=True)
    (e / "review" / ("." + OLD)).write_text("{}", encoding="utf-8")
    (e / "review" / (OLD + ".json")).write_text("[]", encoding="utf-8")
    (e / "review" / (OLD + ".t1.json")).write_text("[]", encoding="utf-8")
    _jsave(e / "review.json", {OLD: {"last": {"session": "s"}}, "trials": {"versions": [{"kinds": [OLD]}, {"kinds": ["hooks"]}]}})
    _jsave(e / "scene.json", {"tracks": [{"items": [{"id": "a", "by": OLD}, {"id": "b"}]}]})
    edit(e)
    assert (e / "review" / ".kiro").exists() and not (e / "review" / ("." + OLD)).exists()
    assert (e / "review" / "agent.json").exists() and (e / "review" / "agent.t1.json").exists()
    rj = _jload(e / "review.json")
    assert rj == {"agent": {"last": {"session": "s"}}, "trials": {"versions": [{"kinds": ["kiro"]}, {"kinds": ["hooks"]}]}}, rj
    assert _jload(e / "scene.json")["tracks"][0]["items"][0]["by"] == "kiro"
    _DONE.clear()
    edit(e)   # twice: nothing moves again, nothing breaks
    edit(t / "missing")
    st = {OLD + "_seen": 5, OLD + "_v": "1.0", "jobs": [{"id": "j", OLD: {"opened": True}, "reserved": 1}]}
    assert state(st) and st == {"agent_seen": 5, "agent_v": "1.0", "jobs": [{"id": "j"}]} and not state(st)
    print("legacy demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
