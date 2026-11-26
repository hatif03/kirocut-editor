"""The editor window: open it, and hear what the user does in it.

The window (home.py) and a video's review page (review.py) are local servers. kirocut_open_editor starts or reuses
them and returns their address in the way that fits the IDE (compat.json: a browser tab, the IDE's Simple Browser,
or an extension panel). kirocut_events hands the chat what the user pressed in them (a new video, Send notes, Approve).
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

from server import ToolError, HERE, PLUGIN
from tools import lazy, resolve_edit

LIB = PLUGIN / "lib" / "kirocut"
COMPAT = HERE / "compat.json"
DEFAULTS = {"embed": "browser", "elicitation": "auto", "progress": "notify", "prompt_hook": "inject"}


def compat():
    """The decisions the compatibility spike recorded (docs/KIRO-COMPAT.md), over safe defaults."""
    try:
        return {**DEFAULTS, **json.loads(COMPAT.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def wait_for(fn, seconds, step=0.25):
    end = time.time() + seconds
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return fn()


def server_env():
    """What the window and review servers run with when this MCP server starts them: they know the chat is in the IDE
    (no Terminal is ever opened for Kiro) and which session their jobs belong to."""
    return {**os.environ, "KIROCUT_IDE": "1", "KIROCUT_NO_REOPEN": "1", "PYTHONUTF8": "1"}


def note_pid(path, pid):
    """Remember a server this module started, so a test or a clean-up can stop exactly it."""
    try:
        Path(path).write_text(str(pid), encoding="utf-8")
    except OSError:
        pass


def stop_servers(*pid_files):
    """End the servers whose pid files these are (best effort)."""
    import signal
    for f in pid_files:
        try:
            os.kill(int(Path(f).read_text(encoding="utf-8")), signal.SIGTERM)
        except (OSError, ValueError):
            pass


def ensure_home():
    """(address of the window, started now)."""
    home = lazy("home")
    url = home.running()
    if url:
        return url, False
    import proc
    log = home.home().parent / "home-server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    p = proc.spawn([sys.executable, str(LIB / "home.py"), "serve", "--no-open"], env=server_env(), log=log)
    note_pid(home.home() / "server.pid", p.pid)
    url = wait_for(home.running, 25)
    if not url:
        raise ToolError("editor_not_started", "the editor window did not start", f"look at {log}, or run kirocut_status")
    return url, True


def start_raw(folder, source):
    """Round 0 on the raw take: the page opens at once and plays it while Kiro cuts (review.py start --raw)."""
    src = Path(source).expanduser()
    if not src.is_file():
        raise ToolError("no_source", f"no video at {source}", "pass the raw take's path as source")
    folder.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(LIB / "review.py"), str(folder), "start", "--raw", "--stage", "cut",
                        "--video", str(src.resolve())], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise ToolError("no_review", (r.stderr or r.stdout).strip()[-300:] or "review.py start failed", "")


def ensure_review(folder, source=None):
    """(address of the edit's review page, started now). With `source` and no page yet: round 0 on the raw take."""
    review = lazy("review")
    if not (folder / "review.json").is_file() and source:
        start_raw(folder, source)
    if not (folder / "review.json").is_file():
        raise ToolError("no_review", f"{folder.name} has no review page yet",
                        "pass source (the raw take) to open it while you cut, or open it after review.py start")
    url = review.running(folder)
    if url:
        return url, False
    import proc
    log = folder / "review" / "server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    p = proc.spawn([sys.executable, str(LIB / "review.py"), str(folder), "serve", "--no-open"], env=server_env(), log=log)
    note_pid(folder / "review" / "server.pid", p.pid)
    url = wait_for(lambda: review.running(folder), 30)
    if not url:
        raise ToolError("editor_not_started", f"the review page for {folder.name} did not start", f"look at {log}")
    return url, True


def present(url, tier=None, open_browser=True):
    """How the user gets to this address in the IDE, by tier. The address itself is always in the result."""
    tier = tier or compat()["embed"]
    embed = url + ("&" if "?" in url else "?") + "embed=1"
    out = {"url": url, "embed_url": embed, "tier": tier, "opened_in_browser": False}
    if tier == "simple-browser":
        out["markdown"] = "[Open KiroCut in the IDE](command:simpleBrowser.show?" + urllib.parse.quote(json.dumps([embed]), safe="") + ")"
        out["tell_user"] = "Click the link to open the editor beside the chat. Include the markdown link in your reply exactly as written."
    elif tier == "extension":
        out["markdown"] = "[Open KiroCut in the IDE](kiro://kirocut.kirocut-view/open?url=" + urllib.parse.quote(embed, safe="") + ")"
        out["tell_user"] = "Click the link to open the editor panel. Include the markdown link in your reply exactly as written."
    else:
        out["markdown"] = f"[Open KiroCut]({url})"
        if open_browser and not os.environ.get("KIROCUT_NO_BROWSER"):
            try:
                out["opened_in_browser"] = bool(webbrowser.open(url))
            except Exception:   # noqa: BLE001
                pass
        out["tell_user"] = "The editor opened in your browser." if out["opened_in_browser"] else "Open the link to see the editor."
    return out


def register(s):
    @s.tool("kirocut_open_editor",
            "Start (or reuse) the KiroCut editor window and show it to the user. With no edit it is the home window (new video, "
            "your videos, styles, settings). With an edit it is that video's review page (timeline, notes, Approve). The result has the "
            "address, and a markdown link to show the user in your reply. Call kirocut_events afterwards to hear what they do there.",
            {"type": "object", "properties": {
                "edit": {"type": "string", "description": "An edit folder or name for its review page. Omit for the home window."},
                "source": {"type": "string", "description": "The raw take, for an edit with no page yet: the page opens now and plays "
                                                            "it while you cut, ticking off each step and striking the words you cut"},
                "open_browser": {"type": "boolean", "description": "Open the system browser when the IDE has no panel for it (default true)"}}})
    def kirocut_open_editor(ctx, edit=None, source=None, open_browser=True):
        if edit:
            try:
                folder = resolve_edit(edit)
            except ToolError:
                if not source:
                    raise
                p = Path(str(edit)).expanduser()   # a new edit: its folder, or edits/<name> in the library
                folder = (p if p.is_absolute() else lazy("library").path() / "edits" / p.name).resolve()
            url, started = ensure_review(folder, source)
            kind = "edit"
        else:
            url, started = ensure_home()
            kind = "home"
        out = present(url, open_browser=bool(open_browser))
        out.update(kind=kind, started=started)
        if edit:
            out["edit"] = str(folder)
        return out

    @s.tool("kirocut_events",
            "Hear what the user did in the editor window: a video or job they started (JOB lines to carry out), notes they sent on a draft, "
            "Approve, a rule they accepted. Waits up to wait_s seconds, then returns what is there (an empty list means nothing happened yet). "
            "Each event is delivered once. While a draft is with the user, call this again and again until they approve; between calls the "
            "window shows Kiro as busy, not listening. Answer each notes event by changing the scene (kirocut_scene_ops), then hand back with "
            "kirocut_review_round.",
            {"type": "object", "properties": {
                "wait_s": {"type": "number", "description": "Seconds to wait for something (0 to 55, default 20)"}}})
    def kirocut_events(ctx, wait_s=20):
        import events
        t0 = time.time()
        got = events.poll(min(max(float(wait_s), 0.0), 55.0), ctx)
        return {"events": got, "count": len(got), "waited_s": round(time.time() - t0, 1),
                "next": ("Act on each event, then call kirocut_events again." if got else
                         "Nothing yet. Tell the user you are waiting only if they expect something, and call kirocut_events again when they say they sent it.")}

    @s.tool("kirocut_replay",
            "Make a time-lapse of how Kiro made an edit: every step and every change, about a second each, labelled, over a frame of the "
            "video as it was then. Use when the user asks to see how the edit was made, or for a demo. Returns the file and its address on "
            "the review page.",
            {"type": "object", "required": ["edit"], "properties": {
                "edit": {"type": "string", "description": "The edit: its folder, or its name in the library"},
                "each": {"type": "number", "description": "Seconds per moment (0.3 to 4, default 1.4)"}}})
    def kirocut_replay(ctx, edit, each=1.4):
        folder = resolve_edit(edit)
        each = min(max(float(each), 0.3), 4.0)
        r = subprocess.run([sys.executable, str(LIB / "replay.py"), "build", str(folder), "--each", str(each)],
                           capture_output=True, text=True, timeout=900)
        if r.returncode:
            msg = (r.stderr or r.stdout).strip().splitlines()
            raise ToolError("replay_failed", (msg[-1] if msg else "replay.py build failed")[:300],
                            "it needs steps, changes or drafts recorded: make or change the edit first")
        out = folder / "review" / "replay.mp4"
        url = lazy("review").running(folder)
        res = {"file": str(out), "summary": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""}
        if url:
            base, _, q = url.partition("?")
            res["url"] = base.rstrip("/") + "/replay.mp4?" + q
        return res
