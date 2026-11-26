#!/usr/bin/env python3
"""A small vision model on this computer looks at an edit's frames, the way a person would: a face covered, a caption
hard to read, a frame that looks machine-made. Stdlib only; the model runs in Ollama (local, free, no key).

    python3 vision.py status                 is Ollama running, and with which models
    python3 vision.py review <edit|folder>   ask about every still (<edit>/stills/*.png, or a folder of PNG/JPG)
    python3 vision.py demo                   self-check against a fake Ollama (no model needed)

Install once, in your own terminal: Windows `winget install -e --id Ollama.Ollama`, Mac `brew install ollama`, then
`ollama pull moondream` (about 1.7 GB; runs on the CPU). KIROCUT_VISION_MODEL picks another (qwen2.5vl:3b reads text
better and is larger), OLLAMA_HOST another address. With no Ollama the review is skipped with one line, never a failure.
check.py render and stills add its findings as WARN (a face covered, a caption not readable) and LOOK (a machine-made look).
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.environ.get("KIROCUT_VISION_MODEL", "moondream")
TIMEOUT_S = 120
# (key, question, the answer that is a problem, level, what to do)
QUESTIONS = [
    ("face", "Is a person's face hidden behind a picture, a box or text in this frame? Answer only yes or no.", "yes", "WARN",
     "move the card off the face (overlays skill), or let the cut-away take the whole frame"),
    ("caption", "Is there text along the bottom of this frame, and is it easy to read? Answer only yes or no.", "no", "WARN",
     "captions larger or on a darker band (plan again: plan.py steps the contrast up)"),
    ("ai", "Does this frame look like an AI-generated image or a generic stock template? Answer only yes or no.", "yes", "LOOK",
     "show the real thing named instead (a capture, the user's own footage)"),
]


def host():
    h = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    return h if h.startswith("http") else "http://" + h


def models(url=None, timeout=3):
    """The models Ollama has, or None when it is not running."""
    try:
        with urllib.request.urlopen((url or host()) + "/api/tags", timeout=timeout) as r:
            return [m.get("name", "") for m in json.loads(r.read()).get("models") or []]
    except (OSError, ValueError, urllib.error.URLError):
        return None


def has_model(names, model=MODEL):
    return any(n == model or n.split(":")[0] == model.split(":")[0] for n in names or [])


def ask(image, question, model=MODEL, url=None, timeout=TIMEOUT_S):
    """The model's answer to one question about one image, as text."""
    body = json.dumps({"model": model, "prompt": question, "stream": False, "options": {"temperature": 0},
                       "images": [base64.b64encode(Path(image).read_bytes()).decode()]}).encode()
    req = urllib.request.Request((url or host()) + "/api/generate", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return str(json.loads(r.read()).get("response") or "").strip()


def yes_no(text):
    """'yes', 'no' or None from a model's reply ("Yes.", "No, the text is clear", "I think so" -> None)."""
    m = re.match(r"\W*(yes|no)\b", text.lower())
    return m.group(1) if m else None


def stills_of(target):
    p = Path(target)
    d = p / "stills" if (p / "stills").is_dir() else p
    return sorted([*d.glob("*.png"), *d.glob("*.jpg")], key=lambda f: f.name) if d.is_dir() else []


def review(target, model=MODEL, url=None, limit=24):
    """{ran, why, findings: [{still, check, level, answer, fix}], asked}. Skipped (ran False) with the reason when Ollama or
    the model is missing; a still the model cannot answer is left out, never guessed."""
    names = models(url)
    if names is None:
        return {"ran": False, "why": "Ollama is not running (vision.py: install it and `ollama pull moondream`)", "findings": []}
    if not has_model(names, model):
        return {"ran": False, "why": f"Ollama has no {model} model: `ollama pull {model}`", "findings": []}
    stills = [s for s in stills_of(target) if s.name != "sheet.png"][:limit]
    out, asked = [], 0
    for s in stills:
        for key, q, bad, level, fix in QUESTIONS:
            try:
                a = yes_no(ask(s, q, model, url))
            except (OSError, ValueError, urllib.error.URLError):
                continue
            asked += 1
            if a == bad:
                out.append({"still": s.name, "check": key, "level": level, "answer": a, "fix": fix})
    return {"ran": True, "why": None, "findings": out, "asked": asked, "stills": len(stills), "model": model}


def lines(res):
    """check.py's lines for a review: one per finding, or the one line that says why it was skipped."""
    if not res["ran"]:
        return [f"note: vision check skipped: {res['why']}"]
    what = {"face": "a face looks covered", "caption": "the caption looks hard to read", "ai": "the frame looks machine-made"}
    return [f"{f['level']:<5} {f['still']}: {what[f['check']]} ({res['model']})\n        -> {f['fix']}" for f in res["findings"]] \
        or [f"vision: {res['stills']} stills, nothing a person would notice ({res['model']})"]


def demo():
    import threading
    import tempfile
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    answers = {"face": "Yes, the face is behind a card.", "caption": "No.", "ai": "I am not sure."}
    seen = []

    class Fake(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            body = json.dumps({"models": [{"name": "moondream:latest"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(req)
            key = next(k for k, q, *_ in QUESTIONS if q == req["prompt"])
            body = json.dumps({"response": answers[key]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert [yes_no(t) for t in ("Yes.", "no, it is clear", " YES", "I think so", "")] == ["yes", "no", "yes", None, None]
        with tempfile.TemporaryDirectory() as t:
            st = Path(t) / "stills"
            st.mkdir()
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
            for n in ("4-card.png", "5-card.png", "sheet.png"):
                (st / n).write_bytes(png)
            res = review(t, url=url)
            assert res["ran"] and res["stills"] == 2 and res["asked"] == 6, res   # the contact sheet is not a frame
            got = {(f["still"], f["check"], f["level"]) for f in res["findings"]}
            assert got == {("4-card.png", "face", "WARN"), ("5-card.png", "face", "WARN"), ("4-card.png", "caption", "WARN"),
                           ("5-card.png", "caption", "WARN")}, got   # "not sure" about the AI look: no finding
            assert all(r["model"] == "moondream" and r["images"] and r["options"]["temperature"] == 0 for r in seen), seen[0].keys()
            ls = lines(res)
            assert len(ls) == 4 and ls[0].startswith("WARN") and "->" in ls[0], ls
            assert review(t, model="llava", url=url)["why"].startswith("Ollama has no llava")
        off = review(".", url="http://127.0.0.1:9")   # nothing listening: skipped with the reason
        assert not off["ran"] and "not running" in off["why"] and lines(off)[0].startswith("note: vision check skipped")
    finally:
        srv.shutdown()
        srv.server_close()
    print("vision demo ok")


def main(argv):
    if argv[:1] == ["demo"]:
        return demo()
    if argv[:1] == ["status"]:
        names = models()
        print("Ollama not running" if names is None else f"Ollama: {', '.join(names) or 'no models'}; "
              f"{MODEL} {'ready' if has_model(names) else 'missing: ollama pull ' + MODEL}")
        return 0 if names is not None and has_model(names) else 1
    if argv[:1] == ["review"] and len(argv) == 2:
        print("\n".join(lines(review(argv[1]))))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
