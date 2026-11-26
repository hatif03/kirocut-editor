#!/usr/bin/env python3
"""The commands behind KiroCut's Kiro IDE hooks (.kiro/hooks/kirocut.json). Standard library only.

Kiro runs a hook command with the event JSON on stdin; on exit 0 whatever it prints is added to the agent's context.

    kirohook.py prompt     PromptSubmit: if the user did something in the editor window since the agent last looked
                           (a new video, notes sent, Approve), say so in one line so the agent calls kirocut_events.
                           Nothing is taken here (kirocut_events delivers each event once). Lifts a window Stop.
    kirohook.py pretool    PreToolUse on every tool: the window's Stop denies tool calls for STOP_S seconds
                           (exit 2, the reason on stderr), so a long run ends at its next step
    kirohook.py stop       Stop: the agent's turn ended, so the window stops saying "Kiro is listening"
    kirohook.py session    SessionStart: one line only when a tool KiroCut needs is missing, silent when everything is ready
    kirohook.py demo       self-check

Every mode exits 0 on any error (a broken hook must never block the user), except pretool's deliberate exit 2.
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "mcp"))

STOP_S = 120
REASON = ("The user pressed Stop in the KiroCut window. Stop now: call no more tools. Say in one line what was left "
          "unfinished, then wait for the user to write to you.")


def kiro_home():
    return Path(os.environ.get("KIROCUT_HOME", "").strip() or Path.home() / ".kirocut")


def stop_dir():
    return kiro_home() / "stop"


def stopped(now=None):
    """True while a window Stop is fresh. Old Stop files are removed."""
    now = now or time.time()
    hit = False
    try:
        for f in stop_dir().iterdir():
            try:
                if now - f.stat().st_mtime < STOP_S:
                    hit = True
                else:
                    f.unlink()
            except OSError:
                pass
    except OSError:
        pass
    return hit


def lift_stop():
    try:
        for f in stop_dir().iterdir():
            f.unlink(missing_ok=True)
    except OSError:
        pass


def waiting_line():
    """One line about what waits in the window, or "" when nothing does."""
    import events   # mcp/events.py
    s = events.scan()
    bits = []
    if s["jobs"]:
        bits.append(f"{s['jobs']} job{'s' if s['jobs'] != 1 else ''} started in the window")
    if s["reviews"]:
        names = ", ".join(Path(f).name for f in s["reviews"][:3])
        bits.append(f"notes or an approval on {names}")
    if not bits:
        return ""
    return ("KiroCut: the user did something in the editor window: " + "; ".join(bits) +
            ". Call kirocut_events now (wait_s 0) and act on what it returns before anything else.")


def session_line():
    """The SessionStart line: what to fix first, or "" when KiroCut is ready."""
    import importlib.util
    setup_py = HERE.parents[1] / "skills" / "setup" / "scripts" / "setup.py"
    spec = importlib.util.spec_from_file_location("kirocut_setup", setup_py)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    lines = []
    if workspace_unconnected():
        lines.append("The kirocut tools are not connected in this workspace. Ask the user to run this once in their own terminal, "
                     f"then reload the window: node plugins/kirocut/mcp/launch.mjs --run {setup_py.relative_to(HERE.parents[3]).as_posix()} workspace")
    bad = [n for n, ok, _, _ in m.checks() if not ok and n in ("python", "ffmpeg", "node", "python packages", "renderer", "transcription model")]
    if bad:
        lines.append("KiroCut is not set up yet: " + ", ".join(bad) + " missing. Before editing, call kirocut_status (it starts "
                     "installing what it can by itself), tell the user in one line, and run the setup skill for the rest.")
    return " ".join(lines)


def workspace_unconnected(repo=None):
    """True when this is the clone (the repo's .kiro is here) and its .kiro/settings/mcp.json has no kirocut server. A power
    install brings its own server, so a folder without the repo's .kiro is never flagged."""
    repo = Path(repo) if repo else HERE.parents[3]
    if not (repo / ".kiro" / "hooks").is_dir() or os.environ.get("KIROCUT_POWER"):
        return False
    try:
        return "kirocut" not in (json.loads((repo / ".kiro" / "settings" / "mcp.json").read_text(encoding="utf-8")).get("mcpServers") or {})
    except (OSError, ValueError):
        return True


def main(mode):
    try:
        try:
            json.loads(sys.stdin.read() or "{}")
        except (ValueError, OSError):
            pass
        if mode == "pretool":
            if stopped():
                sys.stderr.write(REASON)
                return 2
            return 0
        if mode == "prompt":
            lift_stop()
            line = waiting_line()
            if line:
                print(line)
        elif mode == "stop":
            import events
            events.beat(False)
        elif mode == "session":
            line = session_line()
            if line:
                print(line)
    except Exception:   # noqa: BLE001  a hook never blocks the user
        pass
    return 0


def demo():
    import io
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="kirohook_demo_"))
    os.environ["KIROCUT_HOME"] = str(tmp / "home")
    os.environ["KIROCUT_LIBRARY"] = str(tmp / "lib")
    # Stop: fresh file denies, an old one lifts and is removed, the next prompt lifts it at once
    assert not stopped()
    stop_dir().mkdir(parents=True)
    (stop_dir() / "s1").write_text("x", encoding="utf-8")
    assert stopped() and not stopped(now=time.time() + STOP_S + 1) and not (stop_dir() / "s1").exists()
    (stop_dir() / "s2").write_text("x", encoding="utf-8")
    real_in, sys.stdin = sys.stdin, io.StringIO("{}")
    try:
        real_err, sys.stderr = sys.stderr, io.StringIO()
        try:
            assert main("pretool") == 2, "a fresh Stop denies the tool"
            assert "pressed Stop" in sys.stderr.getvalue(), "the reason goes to stderr, where Kiro reads it"
        finally:
            sys.stderr = real_err
        sys.stdin = io.StringIO("{}")
        out, real_out = io.StringIO(), sys.stdout
        sys.stdout = out
        assert main("prompt") == 0
        sys.stdout = real_out
        assert not stopped() and out.getvalue() == "", "the user's next message lifts Stop; nothing waits, nothing is printed"
        sys.stdin = io.StringIO("{}")
        assert main("pretool") == 0
        # a job started in the window: the prompt hook says so, once per call, without taking it
        import home
        home.update(lambda d: home.queue(d, "teardown", {"handle": "x", "platform": "youtube"}))
        assert "1 job started in the window" in waiting_line() and "kirocut_events" in waiting_line()
        assert "1 job started in the window" in waiting_line(), "announcing is not taking"
        sys.stdin = io.StringIO("not json")
        assert main("nonsense") == 0, "an unknown mode and bad input are harmless"
    finally:
        sys.stdin = real_in
    # the clone with no workspace mcp.json: the session line gives the one command; connected, or a power install: silent on it
    ws = tmp / "repo"
    (ws / ".kiro" / "hooks").mkdir(parents=True)
    assert workspace_unconnected(ws)
    (ws / ".kiro" / "settings").mkdir()
    (ws / ".kiro" / "settings" / "mcp.json").write_text(json.dumps({"mcpServers": {"other": {}}}), encoding="utf-8")
    assert workspace_unconnected(ws), "another server only: still not connected"
    (ws / ".kiro" / "settings" / "mcp.json").write_text(json.dumps({"mcpServers": {"kirocut": {}}}), encoding="utf-8")
    assert not workspace_unconnected(ws) and not workspace_unconnected(tmp / "elsewhere")
    print("kirohook demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        sys.exit(main((sys.argv[1:] or [""])[0]))
