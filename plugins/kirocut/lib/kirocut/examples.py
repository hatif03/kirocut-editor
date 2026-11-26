#!/usr/bin/env python3
"""Edits KiroCut made, kept as examples anyone using the editor can watch (the home window's Examples, the README).

    python3 examples.py save <edit> <name> --title T --what W --license L [--source URL] [--credit C] [--own]
                             [--stage cut|edit] [--video FILE] [--from S]    add or update an example
    python3 examples.py list                                                 the examples, newest first
    python3 examples.py demo                                                 self-check (ffmpeg only)

An example is docs/examples/<name>/ in the repo: preview.mp4 (the finished video, at most PREVIEW_S, 720p, small enough
for git), poster.jpg, replay.mp4 when the edit has one (replay.py), before.mp4 (the same moment of the raw take, when there
is one) and meta.json; docs/examples/index.json lists them all. The full-length files stay in the user's library.

Only footage anyone may publish becomes an example: public domain, CC0 or CC BY (the credit is kept and shown), or the
user's own footage (--own, their say-so). Another creator's video never does, and a link to a social account
(Instagram, TikTok, YouTube) is refused as a source: those are measured as references and stay on the user's machine.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STORE = ROOT / "docs" / "examples"
PREVIEW_S = 45
OPEN = re.compile(r"^(public domain|cc0|cc by(-sa)?( \d\.\d)?|own footage)\b", re.I)
SOCIAL = re.compile(r"(instagram\.com|tiktok\.com|youtube\.com|youtu\.be)", re.I)
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")


def duration(p):
    try:
        return round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                           str(p)], capture_output=True, text=True, timeout=60).stdout.strip() or 0), 2)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def outputs(edit):
    """(raw take, cut, finished edit, replay) of an edit folder, each a path or None."""
    edit = Path(edit)
    try:
        rj = json.loads((edit / "review.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rj = {}
    raw = next((r.get("video") for r in rj.get("rounds") or [] if r.get("round") == 0 and r.get("video")), None)
    if not raw and (edit / "takes.txt").exists():
        raw = ((edit / "takes.txt").read_text(encoding="utf-8").split() or [None])[0]
    finished = sorted([*edit.glob("render.mp4"), *edit.glob("exports/*.mp4")], key=lambda p: p.stat().st_mtime)
    ok = lambda p: Path(p) if p and Path(p).is_file() else None   # noqa: E731
    return ok(raw), ok(edit / "cut.mp4"), ok(finished[-1] if finished else None), ok(edit / "review" / "replay.mp4")


def check_rights(license, source, own):
    if own:
        return "own footage"
    if not license or not OPEN.match(license.strip()):
        raise SystemExit("an example needs footage anyone may publish: --license 'Public domain', 'CC0', 'CC BY 4.0', "
                         "or --own for the user's own footage")
    if source and SOCIAL.search(source):
        raise SystemExit("a social account's video is a reference, never an example: it stays on this machine")
    return license.strip()


def clip(src, out, start, secs, height=720, crf=28, audio=True):
    vf = f"scale=-2:{height}:flags=lanczos,fps=30"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{secs:.2f}", "-i", str(src), "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    cmd += ["-c:a", "aac", "-b:a", "96k"] if audio else ["-an"]
    if subprocess.run(cmd + [str(out)], capture_output=True).returncode and audio:   # a silent source
        subprocess.run(cmd[:cmd.index("-c:a")] + ["-an", str(out)], check=True, capture_output=True)
    return out


def save(edit, name, title, what, license=None, source=None, credit=None, own=False, stage=None, video=None,
         start=None, store=STORE, raw_take=None):
    """Write (or refresh) docs/examples/<name>/ and its row in index.json; returns the row."""
    if not NAME.match(name):
        raise SystemExit(f"name {name!r}: lowercase letters, digits and hyphens")
    rights = check_rights(license, source, own)
    edit = Path(edit).resolve()
    raw, cut, finished, replay = outputs(edit)
    raw = Path(raw_take) if raw_take and Path(raw_take).is_file() else raw
    show = Path(video) if video else (cut if stage == "cut" else finished or cut)
    if not show or not show.is_file():
        raise SystemExit(f"{edit.name} has no {'cut' if stage == 'cut' else 'finished video'} yet")
    lens = {k: duration(p) for k, p in (("raw", raw), ("cut", cut), ("edit", finished)) if p}
    total = duration(show)
    at = start if start is not None else max(0.0, min(total - PREVIEW_S, total * 0.15)) if total > PREVIEW_S else 0.0
    secs = min(PREVIEW_S, max(1.0, total - at))
    d = Path(store) / name
    d.mkdir(parents=True, exist_ok=True)
    clip(show, d / "preview.mp4", at, secs)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at + secs / 3:.2f}", "-i", str(show), "-frames:v", "1",
                    "-vf", "scale=-2:360", "-q:v", "4", str(d / "poster.jpg")], check=True, capture_output=True)
    files = ["preview.mp4", "poster.jpg"]
    if replay:
        clip(replay, d / "replay.mp4", 0, min(90, duration(replay)), crf=30, audio=False)
        files.append("replay.mp4")
    if raw and show == cut:   # the cut against the take: the first PREVIEW_S of the take, raw
        clip(raw, d / "before.mp4", 0, min(PREVIEW_S, duration(raw)))
        files.append("before.mp4")
    row = {"name": name, "title": title, "what": what, "stage": stage or ("cut" if show == cut else "edit"),
           "license": rights, "source": source, "credit": credit, "lengths_s": lens, "preview": {"from_s": round(at, 2), "seconds": round(secs, 2)},
           "files": files, "saved": datetime.date.today().isoformat(),
           "full": {k: str(p) for k, p in (("raw", raw), ("cut", cut), ("edit", finished)) if p}}
    (d / "meta.json").write_text(json.dumps({k: v for k, v in row.items() if k != "full"}, indent=2) + "\n", encoding="utf-8")
    idx = Path(store) / "index.json"
    try:
        rows = json.loads(idx.read_text(encoding="utf-8")).get("examples") or []
    except (OSError, ValueError):
        rows = []
    rows = [r for r in rows if r.get("name") != name] + [{k: v for k, v in row.items() if k != "full"}]
    rows.sort(key=lambda r: r.get("saved", ""), reverse=True)
    idx.write_text(json.dumps({"examples": rows}, indent=2) + "\n", encoding="utf-8")
    mb = sum((d / f).stat().st_size for f in files) / 1e6
    print(f"{d}: {', '.join(files)} ({mb:.1f} MB); full-length files stay in the library: {', '.join(row['full'].values())}")
    return row


def listing(store=STORE):
    try:
        return json.loads((Path(store) / "index.json").read_text(encoding="utf-8")).get("examples") or []
    except (OSError, ValueError):
        return []


def demo():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        e, store = t / "edits" / "talk", t / "examples"
        (e / "review").mkdir(parents=True)
        for name, src, dur in (("take.mp4", "testsrc2", 70), ("cut.mp4", "smptebars", 50), ("render.mp4", "testsrc", 50)):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size=1280x720:rate=30:duration={dur}",
                            "-f", "lavfi", "-i", f"sine=frequency=330:duration={dur}", "-shortest", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", str(e / name)], check=True)
        (e / "review.json").write_text(json.dumps({"rounds": [{"stage": "cut", "round": 0, "video": str(e / "take.mp4")}]}), encoding="utf-8")
        for bad in ({"license": None}, {"license": "All rights reserved"},
                    {"license": "CC BY 4.0", "source": "https://www.tiktok.com/@someone/video/1"}):
            try:
                save(e, "talk", "T", "W", store=store, **bad)
                raise AssertionError(f"saved without the rights to publish: {bad}")
            except SystemExit:
                pass
        try:
            save(e, "Bad Name", "T", "W", license="CC0", store=store)
            raise AssertionError("a bad name was taken")
        except SystemExit:
            pass
        r = save(e, "talk", "A talk, cut", "a 70 s take cut to 50 s", license="Public domain", credit="NASA", store=store, stage="cut")
        assert r["stage"] == "cut" and r["files"] == ["preview.mp4", "poster.jpg", "before.mp4"], r
        assert r["preview"] == {"from_s": 5.0, "seconds": 45.0} and r["lengths_s"]["raw"] == 70.0, r
        h = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=height", "-of", "csv=p=0",
                            str(store / "talk" / "preview.mp4")], capture_output=True, text=True).stdout.strip()
        assert h == "720" and abs(duration(store / "talk" / "preview.mp4") - 45) < 0.5, h
        r2 = save(e, "talk-edit", "A talk, styled", "the edit", own=True, store=store)
        assert r2["stage"] == "edit" and r2["license"] == "own footage" and "before.mp4" not in r2["files"], r2
        save(e, "talk", "A talk, cut", "again", license="CC0", store=store, stage="cut")   # the same name updates its row
        names = [x["name"] for x in listing(store)]
        assert sorted(names) == ["talk", "talk-edit"], names
        meta = json.loads((store / "talk" / "meta.json").read_text(encoding="utf-8"))
        assert "full" not in meta and meta["what"] == "again" and meta["license"] == "CC0", "no local paths in the repo"
    print("examples demo ok")


def main(argv):
    ap = argparse.ArgumentParser(description="Keep an edit as an example anyone can watch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("edit")
    s.add_argument("name")
    s.add_argument("--title", required=True)
    s.add_argument("--what", required=True)
    s.add_argument("--license")
    s.add_argument("--source")
    s.add_argument("--credit")
    s.add_argument("--own", action="store_true")
    s.add_argument("--stage", choices=["cut", "edit"])
    s.add_argument("--video")
    s.add_argument("--from", dest="start", type=float)
    s.add_argument("--raw", help="the raw take, when the edit has no review page that names it")
    sub.add_parser("list")
    sub.add_parser("demo")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        return demo()
    if a.cmd == "list":
        for r in listing():
            print(f"{r['name']:<24} {r['stage']:<5} {r['license']:<16} {r['title']}")
        return 0
    save(a.edit, a.name, a.title, a.what, a.license, a.source, a.credit, a.own, a.stage, a.video, a.start, raw_take=a.raw)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
