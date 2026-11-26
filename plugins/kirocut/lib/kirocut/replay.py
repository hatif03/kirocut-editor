#!/usr/bin/env python3
"""A time-lapse of how Kiro made an edit: every step and every change, a second or so each, labelled.

    python3 replay.py note  <edit> <kind> <text> [--t SECONDS]   record one moment (scripts and tools call note())
    python3 replay.py build <edit> [--out FILE] [--each 1.4]     write <edit>/review/replay.mp4
    python3 replay.py demo                                       self-check (ffmpeg only)

What it reads, in time order:
  review/replay.jsonl   moments noted as they happened (the cut's steps from progress.py, review status lines)
  review/agent.json     Kiro's scene changes ("Add the link at 0:12"), each with the time in the video it touched
  review.json rounds    each draft that landed on the page (the cut, round 2, the edit)
Each moment becomes a short shot: a frame of the video as it was then (the raw take before the cut, the cut before the
edit, the edit after), a slow push in, and the moment's words along the bottom with "3 of 14". A title opens it and the
lengths close it. Stdlib and ffmpeg only; a machine with no font draws the shots without words.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

W, H = 1280, 720
FONTS = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]
MAX_SHOTS = 40


def journal(folder):
    return Path(folder) / "review" / "replay.jsonl"


def note(folder, kind, text, t=None):
    """Record one moment of the edit. Never raises: the replay is a nicety."""
    try:
        f = journal(folder)
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.time(), "kind": kind, "text": str(text)[:120],
                                 **({"t": float(t)} if t is not None else {})}) + "\n")
        return True
    except Exception:
        return False


def _iso(s):
    """review.json and agent.json times (ISO, local or with an offset) as epoch seconds; None when unreadable."""
    import datetime
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def moments(folder):
    """[{at, kind, text, t?, stage}] in time order: noted moments, Kiro's scene changes and the drafts that landed."""
    folder = Path(folder)
    out = []
    try:
        for ln in journal(folder).read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    for name in ("agent.json",):
        try:
            log = json.loads((folder / "review" / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log = []
        for c in log if isinstance(log, list) else log.get("changes") or []:
            at = _iso(c.get("when")) or c.get("at_s")
            if at and not c.get("undone"):
                out.append({"at": at, "kind": "change", "text": c.get("why") or "a change", "t": c.get("t")})
    try:
        rj = json.loads((folder / "review.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rj = {}
    for r in rj.get("rounds") or []:
        at = _iso(r.get("at"))
        if at and r.get("round", 0) >= 1:
            what = "The cut is ready" if r.get("stage") == "cut" and r["round"] == 1 else \
                f"Draft {r['round']} of the {'cut' if r.get('stage') == 'cut' else 'edit'}"
            out.append({"at": at, "kind": "round", "text": what, "stage": r.get("stage")})
    out.sort(key=lambda m: m["at"])
    return out


def duration(p):
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                    capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def videos(folder):
    """(raw take, cut, edit) paths that exist, each or None."""
    folder = Path(folder)
    try:
        rj = json.loads((folder / "review.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rj = {}
    raw = None
    for r in rj.get("rounds") or []:
        if r.get("round") == 0 and r.get("video"):
            raw = r["video"]
    raw = raw or (rj.get("video") if rj.get("raw") else None)
    if not raw:
        for f in ("takes.txt",):
            if (folder / f).exists():
                first = (folder / f).read_text(encoding="utf-8").split()
                raw = first[0] if first else None
    edits = sorted([*folder.glob("render*.mp4"), *folder.glob("exports/*.mp4")], key=lambda p: p.stat().st_mtime)
    pick = lambda p: str(p) if p and Path(p).is_file() else None   # noqa: E731
    return pick(raw), pick(folder / "cut.mp4"), pick(edits[-1] if edits else None)


def font():
    return next((f for f in FONTS if Path(f).is_file()), None)


def _esc(p):
    """A path inside an ffmpeg filter argument."""
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def shot(src, at, label, counter, out, each, fnt, tmp):
    """One moment: the frame at `at` of `src` (black when none), a slow push in, the words along the bottom."""
    fit = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0f0d16,setsar=1"
    frames = max(2, round(each * 30))
    push = f"zoompan=z='1+0.04*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30"
    words = ""
    if fnt:
        lf, cf = Path(tmp) / f"{out.stem}.txt", Path(tmp) / f"{out.stem}.n.txt"
        lf.write_text(label, encoding="utf-8")
        cf.write_text(counter, encoding="utf-8")
        words = (f",drawbox=y=ih-96:w=iw:h=96:color=0x0f0d16@0.78:t=fill"
                 f",drawtext=fontfile='{_esc(fnt)}':textfile='{_esc(lf)}':fontcolor=white:fontsize=34:x=40:y=h-66"
                 f",drawtext=fontfile='{_esc(fnt)}':textfile='{_esc(cf)}':fontcolor=0xB9A6FF:fontsize=26:x=w-tw-40:y=h-62")
    if src:
        still = Path(tmp) / f"{out.stem}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, at):.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", fit, str(still)], capture_output=True)
        if not still.is_file():   # a moment past the end of a video: the black ground instead
            return shot(None, 0, label, counter, out, each, fnt, tmp)
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "30", "-i", str(still), "-frames:v", str(frames),
               "-vf", push + words, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30", str(out)]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x0f0d16:s={W}x{H}:r=30:d={each}",
               "-vf", "format=yuv420p" + words, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-300:])
    return out


def build(folder, out=None, each=1.4):
    """review/replay.mp4: a title, one shot per moment (at most MAX_SHOTS, evenly kept), the lengths at the end."""
    folder = Path(folder).resolve()
    ms = moments(folder)
    if not ms:
        raise SystemExit(f"nothing to replay yet in {folder.name}: no steps, changes or drafts recorded")
    if len(ms) > MAX_SHOTS:   # keep the first and last, and an even spread between
        step = (len(ms) - 1) / (MAX_SHOTS - 1)
        ms = [ms[round(i * step)] for i in range(MAX_SHOTS)]
    raw, cut, edit = videos(folder)
    lens = {k: duration(v) if v else 0 for k, v in (("raw", raw), ("cut", cut), ("edit", edit))}
    landed_cut = next((m["at"] for m in ms if m["kind"] == "round" and m.get("stage") == "cut"), None)
    landed_edit = next((m["at"] for m in ms if m["kind"] == "round" and m.get("stage") == "edit"), None)
    out = Path(out) if out else folder / "review" / "replay.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    fnt = font()
    with tempfile.TemporaryDirectory() as tmp:
        parts = [shot(None, 0, f"Kiro edits {folder.name}", "KiroCut", Path(tmp) / "s000.mp4", 1.6, fnt, tmp)]
        for i, m in enumerate(ms, 1):
            if m["kind"] == "change" or (landed_edit and m["at"] >= landed_edit):
                src = edit or cut or raw
            elif landed_cut and m["at"] >= landed_cut:
                src = cut or raw
            else:
                src = raw or cut
            key = "edit" if src == edit else "cut" if src == cut else "raw"
            t = m.get("t") if m.get("t") is not None else lens[key] * i / (len(ms) + 1)   # sweep through the video
            parts.append(shot(src, t or 0, m["text"], f"{i} of {len(ms)}", Path(tmp) / f"s{i:03d}.mp4", each, fnt, tmp))
        sizes = " -> ".join(f"{k} {int(v // 60)}:{int(v % 60):02d}" for k, v in lens.items() if v)
        parts.append(shot(edit or cut or raw, (lens["edit"] or lens["cut"] or lens["raw"]) * 0.5, sizes or "Done", "KiroCut",
                          Path(tmp) / "s999.mp4", 2.0, fnt, tmp))
        lst = Path(tmp) / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        "-movflags", "+faststart", str(out)], check=True, capture_output=True)
    print(f"{out}: {len(ms)} moments, {duration(out):.1f} s")
    return out


def demo():
    with tempfile.TemporaryDirectory() as t:
        e = Path(t) / "edits" / "demo"
        (e / "review").mkdir(parents=True)
        for name, src, d in (("take.mp4", "testsrc2", 8), ("cut.mp4", "smptebars", 5), ("render.mp4", "testsrc", 5)):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size=640x360:rate=30:duration={d}",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(e / name)], check=True)
        assert moments(e) == [] and not videos(e)[0]
        try:
            build(e)
            raise AssertionError("an edit with nothing recorded was replayed")
        except SystemExit as err:
            assert "nothing to replay" in str(err)
        base = time.time() - 100
        rec = lambda at, kind, text, **k: (journal(e).open("a", encoding="utf-8").write(   # noqa: E731
            json.dumps({"at": base + at, "kind": kind, "text": text, **k}) + "\n"))
        rec(0, "step", "Writing down every word")
        rec(5, "step", "Cutting out the mistakes")
        import datetime
        iso = lambda s: datetime.datetime.fromtimestamp(base + s).astimezone().isoformat(timespec="seconds")   # noqa: E731
        (e / "review.json").write_text(json.dumps({"rounds": [{"stage": "cut", "round": 0, "video": str(e / "take.mp4"), "at": iso(1)},
                                                              {"stage": "cut", "round": 1, "at": iso(10)},
                                                              {"stage": "edit", "round": 1, "at": iso(30)}]}), encoding="utf-8")
        (e / "review" / "agent.json").write_text(json.dumps([{"n": 1, "why": "Add the link at the end", "t": 4.0, "when": iso(40)},
                                                             {"n": 2, "why": "Undone change", "t": 1.0, "when": iso(41), "undone": True}]),
                                                 encoding="utf-8")
        assert note(e, "step", "Planning zooms, cards and sound") and not note(Path(t) / "nope\0", "step", "x")
        ms = moments(e)
        assert [m["text"] for m in ms] == ["Writing down every word", "Cutting out the mistakes", "The cut is ready",
                                           "Draft 1 of the edit", "Add the link at the end", "Planning zooms, cards and sound"], ms
        assert videos(e) == (str(e / "take.mp4"), str(e / "cut.mp4"), str(e / "render.mp4"))
        out = build(e, each=0.5)
        d = duration(out)
        # title 1.6 s + six moments of 0.5 s + the end 2.0 s
        assert abs(d - (1.6 + 6 * 0.5 + 2.0)) < 0.4, d
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True).stdout.strip()
        assert probe == f"{W},{H}", probe
        assert _esc("C:\\Windows\\Fonts\\a.ttf") == "C\\:/Windows/Fonts/a.ttf"
        for i in range(60):   # a long edit keeps MAX_SHOTS moments, first and last among them
            rec(50 + i, "step", f"moment {i}")
        many = moments(e)
        assert len(many) > MAX_SHOTS
        out2 = build(e, Path(t) / "long.mp4", each=0.2)
        assert abs(duration(out2) - (1.6 + MAX_SHOTS * 0.2 + 2.0)) < 0.6, duration(out2)
    print(f"replay demo ok (labels {'drawn with ' + Path(font()).name if font() else 'off: no font found'})")


def main(argv):
    ap = argparse.ArgumentParser(description="A time-lapse of how Kiro made an edit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("note")
    n.add_argument("edit")
    n.add_argument("kind")
    n.add_argument("text")
    n.add_argument("--t", type=float)
    b = sub.add_parser("build")
    b.add_argument("edit")
    b.add_argument("--out")
    b.add_argument("--each", type=float, default=1.4)
    sub.add_parser("demo")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        return demo()
    if a.cmd == "note":
        return 0 if note(a.edit, a.kind, a.text, a.t) else 1
    build(a.edit, a.out, a.each)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
