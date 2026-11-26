#!/usr/bin/env python3
"""How close is a KiroCut edit to a real video? Measure both with the same code, then compare.

    py tests/bench/bench.py measure <video> <name>          a local video as a style-match "creator"
    py tests/bench/bench.py compare <ref> <ours> [--out DIR] the two measured styles, side by side
    py tests/bench/bench.py demo                            self-check: synthetic styles and clips, no network

Both sides go through style-match's own measuring scripts (transcribe, visual, look, graphics, sound), so a number
on one side means the same thing on the other. `<ref>` and `<ours>` are style-match folders
(<library>/style-matches/<name>/). The report (DIR/report.html, report.json) lists every measured number with the gap
and whether it is inside the tolerance, plus a side-by-side video of the same 20 s from both. Media stays where it was
(the benchmark folder is ~/.kirocut/bench by default): nothing downloaded is written into the repo.
"""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SM = ROOT / "plugins" / "style-match" / "skills" / "style-match" / "scripts"
TOL = 0.25   # a number within 25% of the reference counts as matched

# (label, path in style.json, kind) - kind "num" compares by ratio, "pct" by points (10 points = matched),
# "bool" must be equal, "text" is shown and compared for equality
FIELDS = [
    ("words a minute", "pace.wpm", "num"),
    ("cuts every 10 s", "pace.cuts_per_10s", "num"),
    ("median shot (s)", "pace.median_shot_s", "num"),
    ("longest pause kept (s)", "pace.max_pause_s", "num"),
    ("zooms a minute", "zoom.per_min", "num"),
    ("push-ins a minute", "camera.push_per_min", "num"),
    ("pans a minute", "camera.pan_per_min", "num"),
    ("graphics a minute", "graphics.per_min", "num"),
    ("graphics share of the frame (%)", "graphics.layout.area_pct", "num"),
    ("sound effects a minute", "sound.sfx_per_min", "num"),
    ("music under the voice (% of the video)", "sound.music.present_pct", "pct"),
    ("music level (dB)", "sound.music.level_db", "db"),
    ("captions on screen", "captions.present", "bool"),
    ("words per caption", "captions.words_per_caption", "num"),
    ("caption size (% of height)", "captions.size_pct", "num"),
    ("caption case", "captions.case", "text"),
    ("caption font", "captions.font_match", "text"),
    ("aspect", "aspect", "text"),
]


def get(d, path):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def judge(kind, ref, ours):
    """(gap text, matched: True/False/None when either side is unmeasured)."""
    if ref is None or ours is None:
        return "not measured", None
    if kind == "bool" or kind == "text":
        same = str(ref).lower() == str(ours).lower()
        return ("same" if same else "differs"), same
    if kind == "pct":
        d = ours - ref
        return f"{d:+.0f} points", abs(d) <= 10
    if kind == "db":
        d = ours - ref
        return f"{d:+.1f} dB", abs(d) <= 4
    if ref == 0:
        return ("both 0" if ours == 0 else f"+{ours:g} (ref 0)"), ours == 0
    r = (ours - ref) / abs(ref)
    return f"{r:+.0%}", abs(r) <= TOL


def compare_styles(ref, ours):
    rows = []
    for label, path, kind in FIELDS:
        a, b = get(ref, path), get(ours, path)
        gap, ok = judge(kind, a, b)
        rows.append({"label": label, "field": path, "ref": a, "ours": b, "gap": gap, "matched": ok})
    seen = [r for r in rows if r["matched"] is not None]
    return {"rows": rows, "matched": sum(r["matched"] for r in seen), "measured": len(seen)}


# ---------------------------------------------------------------- measuring
def run(*cmd, cwd=None, env=None):
    print("$", " ".join(Path(str(c)).name if i < 3 else str(c) for i, c in enumerate(cmd)), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
                       capture_output=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    print("  " + "\n  ".join(tail), flush=True)
    return r.returncode


def measure(video, name, lib):
    """Lay `video` out as a one-video style-match folder and run the measuring scripts on it."""
    video, d = Path(video).resolve(), Path(lib) / "style-matches" / name
    (d / "video").mkdir(parents=True, exist_ok=True)
    vid = video.stem.replace(" ", "-")[:40] or "video"
    dst = d / "video" / f"{vid}.mp4"
    if not dst.exists():
        if video.suffix.lower() == ".mp4":
            shutil.copyfile(video, dst)
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "20", "-c:a", "aac", str(dst)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)],
                               capture_output=True, text=True).stdout.strip() or 0)
    (d / "videos.json").write_text(json.dumps({"handle": name, "platform": "local", "profile_url": str(video), "count": 1,
                                               "median_views": 0, "ranked_by": "views", "pasted": True,
                                               "videos": [{"id": vid, "title": video.stem, "duration": round(dur),
                                                           "view_count": 0, "webpage_url": video.as_uri(),
                                                           "vs_median": 1.0, "outlier": False}]}, indent=2),
                                   encoding="utf-8")
    env = {**os.environ, "KIROCUT_LIBRARY": str(lib)}
    vpy = SM / "run.py"
    steps = [(SM / "fetch.py", "transcribe", name), (vpy, SM / "visual.py", "measure", name),
             (vpy, SM / "look.py", "measure", name), (vpy, SM / "graphics.py", "measure", name),
             (vpy, SM / "sound.py", "measure", name)]
    bad = [s for s in steps if run(sys.executable, *s, cwd=lib, env=env)]
    print(f"{d / 'style.json'}" + (f" ({len(bad)} step(s) failed)" if bad else ""))
    return d


# ---------------------------------------------------------------- the report
def first_video(d):
    vs = sorted((Path(d) / "video").glob("*.mp4"))
    return vs[0] if vs else None


def side_by_side(ref_mp4, ours_mp4, out, at=None, secs=20):
    """The same stretch of both, 960x540 each, next to each other, both sounds mixed (ours louder), so a person
    hears and sees both."""
    def dur(p):
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                    capture_output=True, text=True).stdout.strip() or 0)
    a, b = dur(ref_mp4), dur(ours_mp4)
    t = at if at is not None else max(0.0, min(a, b) / 3)
    secs = max(1.0, min(secs, a - t, b - t))
    fit = "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-t", f"{secs:.2f}", "-i", str(ref_mp4),
           "-ss", f"{t:.2f}", "-t", f"{secs:.2f}", "-i", str(ours_mp4),
           "-filter_complex", f"[0:v]{fit}[a];[1:v]{fit}[b];[a][b]hstack=inputs=2[v];"
                              "[0:a]volume=0.35[x];[1:a]volume=1.0[y];[x][y]amix=inputs=2:duration=shortest[au]",
           "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", str(out)]
    if subprocess.run(cmd, capture_output=True).returncode:   # a side with no sound track: picture only
        cmd = cmd[:cmd.index("-filter_complex")] + ["-filter_complex", f"[0:v]{fit}[a];[1:v]{fit}[b];[a][b]hstack=inputs=2[v]",
                                                    "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                                                    "-pix_fmt", "yuv420p", str(out)]
        subprocess.run(cmd, check=True, capture_output=True)
    return {"at": round(t, 2), "seconds": round(secs, 2)}


def write_report(res, out, names, clip=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps({**res, "names": names, "clip": clip}, indent=1, default=str), encoding="utf-8")

    def cell(v):
        return "-" if v is None else html.escape(json.dumps(v) if isinstance(v, (dict, list)) else str(v))
    rows = "".join(
        f"<tr class='{'ok' if r['matched'] else 'no' if r['matched'] is False else 'na'}'><td>{html.escape(r['label'])}</td>"
        f"<td>{cell(r['ref'])}</td><td>{cell(r['ours'])}</td><td>{html.escape(r['gap'])}</td></tr>" for r in res["rows"])
    video = (f"<video src='side-by-side.mp4' controls width='1280'></video><p>Left: {html.escape(names[0])}. "
             f"Right: {html.escape(names[1])}. From {clip['at']} s, {clip['seconds']} s.</p>") if clip else ""
    (out / "report.html").write_text(
        "<!doctype html><meta charset=utf-8><title>KiroCut benchmark</title><style>"
        "body{font:15px system-ui;margin:24px;background:#0f0d16;color:#eee}table{border-collapse:collapse}"
        "td,th{padding:6px 12px;border-bottom:1px solid #333;text-align:left}tr.ok td:last-child{color:#6f6}"
        "tr.no td:last-child{color:#f77}tr.na td{color:#888}h1{color:#b9a6ff}</style>"
        f"<h1>KiroCut benchmark</h1><p><b>{res['matched']} of {res['measured']}</b> measured numbers within tolerance "
        f"(±{TOL:.0%}; music share ±10 points, level ±4 dB).</p>{video}"
        f"<table><tr><th>measure</th><th>{html.escape(names[0])}</th><th>{html.escape(names[1])}</th><th>gap</th></tr>"
        f"{rows}</table>", encoding="utf-8")
    return out / "report.html"


def compare(ref_dir, ours_dir, out):
    load = lambda d: json.loads((Path(d) / "style.json").read_text(encoding="utf-8"))   # noqa: E731
    res = compare_styles(load(ref_dir), load(ours_dir))
    a, b = first_video(ref_dir), first_video(ours_dir)
    Path(out).mkdir(parents=True, exist_ok=True)
    clip = side_by_side(a, b, Path(out) / "side-by-side.mp4") if a and b else None
    page = write_report(res, out, [Path(ref_dir).name, Path(ours_dir).name], clip)
    for r in res["rows"]:
        mark = {True: "ok ", False: "GAP", None: " - "}[r["matched"]]
        print(f"{mark} {r['label']:<40} {cell_txt(r['ref']):>14} {cell_txt(r['ours']):>14}  {r['gap']}")
    print(f"{res['matched']} of {res['measured']} within tolerance -> {page}")
    return res


def cell_txt(v):
    return "-" if v is None else str(v)[:14]


# ---------------------------------------------------------------- self-check
def demo():
    ref = {"aspect": "16:9", "pace": {"wpm": 180, "cuts_per_10s": 2.0, "median_shot_s": 3.1, "max_pause_s": 0.4},
           "zoom": {"per_min": 0}, "camera": {"push_per_min": 1.0, "pan_per_min": 2.0},
           "graphics": {"per_min": 1.5, "layout": {"area_pct": 12}},
           "sound": {"sfx_per_min": 3.0, "music": {"present_pct": 90, "level_db": -24}},
           "captions": {"present": True, "words_per_caption": 6, "size_pct": 2.2, "case": "sentence", "font_match": "EB Garamond"}}
    ours = json.loads(json.dumps(ref))
    ours["pace"].update(cuts_per_10s=0.6, wpm=171)           # far too few cuts; speech pace inside 25%
    ours["sound"].update(sfx_per_min=0, music={"present_pct": 0, "level_db": None})
    ours["captions"].update(words_per_caption=3, size_pct=4.4, font_match="TikTok Sans")
    ours["zoom"]["per_min"] = 2.5                            # zooms where the reference has none
    del ours["graphics"]["layout"]
    res = compare_styles(ref, ours)
    by = {r["field"]: r for r in res["rows"]}
    assert by["pace.wpm"]["matched"] and by["pace.wpm"]["gap"] == "-5%", by["pace.wpm"]
    assert by["pace.cuts_per_10s"]["matched"] is False and by["pace.cuts_per_10s"]["gap"] == "-70%"
    assert by["zoom.per_min"]["matched"] is False and by["zoom.per_min"]["gap"].startswith("+2.5"), by["zoom.per_min"]
    assert by["sound.music.present_pct"]["gap"] == "-90 points" and by["sound.music.present_pct"]["matched"] is False
    assert by["sound.music.level_db"]["matched"] is None, "music not measured on one side: not a match, not a gap"
    assert by["graphics.layout.area_pct"]["matched"] is None and by["captions.font_match"]["matched"] is False
    assert by["aspect"]["matched"] and by["captions.present"]["matched"]
    assert res["measured"] == len(FIELDS) - 2 and res["matched"] == sum(1 for r in res["rows"] if r["matched"])
    assert judge("num", 0, 0) == ("both 0", True) and judge("db", -20, -23) == ("-3.0 dB", True)
    print("compare  ok: ratios, points, dB, equality, unmeasured fields left out")

    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        for name, src in (("ref", "testsrc2=size=640x360:rate=30"), ("ours", "smptebars=size=1280x720:rate=30")):
            (t / name / "video").mkdir(parents=True)
            (t / name / "style.json").write_text(json.dumps(ref if name == "ref" else ours), encoding="utf-8")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src + ":duration=6", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=6", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                            str(t / name / "video" / f"{name}.mp4")], check=True)
        (t / "silent" / "video").mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=6",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(t / "silent" / "video" / "s.mp4")], check=True)
        (t / "silent" / "style.json").write_text(json.dumps(ours), encoding="utf-8")
        r = compare(t / "ref", t / "ours", t / "out")
        page = (t / "out" / "report.html").read_text(encoding="utf-8")
        assert f"<b>{r['matched']} of {r['measured']}</b>" in page and "side-by-side.mp4" in page and "class='no'" in page
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "csv=p=0",
                                str(t / "out" / "side-by-side.mp4")], capture_output=True, text=True).stdout
        assert "video,1920,540" in probe and "audio" in probe, probe
        rep = json.loads((t / "out" / "report.json").read_text(encoding="utf-8"))
        assert rep["names"] == ["ref", "ours"] and rep["clip"]["at"] == 2.0 and rep["clip"]["seconds"] == 4.0, rep["clip"]
        compare(t / "ref", t / "silent", t / "out2")   # a side with no sound still makes the clip
        assert "video,1920,540" in subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                                                   "-of", "csv=p=0", str(t / "out2" / "side-by-side.mp4")],
                                                  capture_output=True, text=True).stdout
    print("report   ok: html and json, 1920x540 side by side with both sounds, a silent side still works")
    print("bench demo ok")


def main(argv):
    ap = argparse.ArgumentParser(description="Measure a KiroCut edit against a real video")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("video")
    m.add_argument("name")
    m.add_argument("--lib", default=os.environ.get("KIROCUT_LIBRARY") or str(Path.home() / ".kirocut" / "bench" / "lib"))
    c = sub.add_parser("compare")
    c.add_argument("ref")
    c.add_argument("ours")
    c.add_argument("--out", default=None)
    sub.add_parser("demo")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        return demo()
    if a.cmd == "measure":
        measure(a.video, a.name, a.lib)
        return 0
    compare(a.ref, a.ours, a.out or Path(a.ours).parent.parent / "bench-report")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
