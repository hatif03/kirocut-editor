#!/usr/bin/env python3
"""kirocut: open the KiroCut window, with Kiro behind it. Stdlib only.

    kirocut                 open the window (the same address every time), with a listening Kiro behind it
    kirocut --window-only   open the window only, never start Kiro
    kirocut --dry-run [--os Darwin|Linux|Windows]   print what it would run, and where
    open_claude(folder, prompt)     a Kiro of its own for each new video (home.py claude_for): a new terminal window
    connect(folder)                 the home page's "Connect Kiro": a new terminal with a listening Kiro
    python3 launcher.py demo        self-check

`setup.py install-launcher` puts the `kirocut` command on the PATH; `uninstall-launcher` takes
it off. Inside Kiro the same thing is the `start` skill, or saying "edit my video".

When the home page is already served, its address opens again in the browser, and when no Kiro is
listening (`home.py wait`), connect() opens one in a new terminal window. Otherwise `kiro-cli chat`
starts in this repo (so `.kiro/skills` load) with one first prompt, PROMPT. Nothing is bypassed:
Kiro's own permissions.yaml decides what runs without asking.
"""
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import home  # noqa: E402
import library  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[2]          # plugins/kirocut
PROMPT = "/kirocut:start open the home page"
LISTEN = "/kirocut:start listen for jobs"   # serve --no-open + wait: takes the queued jobs, not one video
CONNECT_S = 60   # how long a connect counts as pending: the page shows "Opening Kiro..." and no second terminal opens


MARK = "installed by kirocut setup.py install-launcher"
# picks the newest version folder next to this one at run time: /plugin update adds a folder and keeps the old ones
NEWEST = ("import glob,re,sys;d=sys.argv[1];v=lambda p:[int(x) for x in re.findall(r'\\d+',p[len(d):].split('/')[1])[:3]];"
          "print(max(glob.glob(glob.escape(d)+'/*/lib/kirocut/launcher.py'),key=v,default=''))")


def launcher_text(os_name=None, launcher=PLUGIN / "lib" / "kirocut" / "launcher.py", py=sys.executable):
    """The kirocut file. A /plugin install lives in .../kirocut/<version>/: the sh script runs the newest
    version there, so an update never leaves the command on old code. Windows keeps the path home.py refreshes."""
    os_name = os_name or platform.system()
    if os_name == "Windows":
        return (f"@echo off\r\nrem kirocut: opens KiroCut {MARK}; remove with setup.py uninstall-launcher\r\n"
                f'set "L={launcher}"\r\nset "PY={py}"\r\nif not exist "%PY%" set "PY=py"\r\n'
                'if not exist "%L%" (echo KiroCut moved, maybe an update. In Kiro, say: set up the editor. & exit /b 1)\r\n'
                '"%PY%" "%L%" %*\r\n')
    launcher = Path(launcher)
    versions = launcher.parents[3] if "/.kiro/powers/" in launcher.as_posix() else None
    newest = (f"N=$(\"$PY\" -c \"{NEWEST}\" {shlex.quote(versions.as_posix())} 2>/dev/null)\n"
              '[ -n "$N" ] && L="$N"\n') if versions else ""
    return (f"#!/bin/sh\n# kirocut: opens KiroCut {MARK}; remove with setup.py uninstall-launcher\n"
            f"L={shlex.quote(str(launcher))}\nPY={shlex.quote(str(py))}\n[ -x \"$PY\" ] || PY=python3\n" + newest +
            'if [ ! -f "$L" ]; then echo "KiroCut moved, maybe an update. In Kiro, say: set up the editor."; exit 1; fi\n'
            'exec "$PY" "$L" "$@"\n')


def refresh():
    """Rewrite an installed kirocut that points at another copy of the plugin (run by the newest home.py
    serve). Only files this plugin wrote (MARK); never installs one."""
    home_dir = Path.home()
    names = ["kirocut.cmd"] if platform.system() == "Windows" else ["kirocut"]
    dirs = [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p] + [home_dir / ".local" / "bin"]
    for d in dict.fromkeys(dirs):
        for n in names:
            f = d / n
            try:
                old = f.read_text(encoding="utf-8")
            except OSError:
                continue
            want = launcher_text()
            if MARK in old and old != want:
                with open(f, "w", encoding="utf-8", newline="") as fh:
                    fh.write(want)


def workspace(plugin=PLUGIN):
    """Where Kiro should start so this folder's skills load. The repo, when it has .kiro; otherwise the plugin folder."""
    plugin = Path(plugin)
    repo = plugin.parents[1] if len(plugin.parents) > 1 else plugin
    return repo if (repo / ".kiro").is_dir() else plugin


def plan(os_name=None, plugin=PLUGIN, claude=None, prompt=PROMPT, plugins=None, session=None, resume=False, exe=None):
    """The Kiro command: `kiro-cli chat <prompt>`. Skills load because the process starts in this repo.
    `claude` is accepted and ignored. `exe` forces the binary (the self-check). A session id resumes that chat."""
    os_name = os_name or platform.system()
    # kiro.cmd in the IDE install opens the editor. The agent is kiro-cli, a separate program.
    exe = exe or shutil.which("kiro-cli") or ("kiro-cli.exe" if os_name == "Windows" else "kiro-cli")
    cmd = [exe, "chat"]
    if session:
        cmd += ["--resume-id", session]
    elif resume:
        cmd += ["--resume"]
    return cmd + [prompt]


def headless(prompt, exe=None, os_name=None):
    """Kiro with no chat, for a job that must finish on its own (a brand kit, the learn step). Permissions stay
    Kiro's: this does not pass --trust-all-tools."""
    os_name = os_name or platform.system()
    exe = exe or shutil.which("kiro-cli") or ("kiro-cli.exe" if os_name == "Windows" else "kiro-cli")
    return [exe, "chat", "--no-interactive", prompt]


def show(cmd, os_name):
    return subprocess.list2cmdline(cmd) if os_name == "Windows" else shlex.join(cmd)


def terminal(folder, cmd, os_name):
    """The command that opens a new terminal window running cmd in folder, or None when this computer has no
    terminal to open (Linux without x-terminal-emulator): the page then shows the command to copy."""
    if os_name == "Darwin":
        line = f"cd {shlex.quote(str(folder))} && {shlex.join(cmd)}"
        esc = line.replace("\\", "\\\\").replace('"', '\\"')   # inside an AppleScript string
        return ["osascript", "-e", f'tell application "Terminal" to do script "{esc}"',
                "-e", 'tell application "Terminal" to activate']
    if os_name == "Windows":
        # a console of its own (CREATE_NEW_CONSOLE) started in folder, so the folder is never quoted for cmd. One
        # string, not a list: a list would escape the inner quotes as \" (cmd reads them literally); cmd /k
        # strips the outer pair and runs what is inside as typed.
        return f'cmd /k "{subprocess.list2cmdline(cmd)}"'
    xte = shutil.which("x-terminal-emulator")
    if not xte:
        return None
    return [xte, "-e", "sh", "-c", f'cd {shlex.quote(str(folder))} && {shlex.join(cmd)}; exec "${{SHELL:-sh}}"']


def start(argv, folder, os_name):
    """Run terminal()'s command. True only when the window opened (as far as the OS says). KIROCUT_NO_REOPEN (tests,
    review.py): never."""
    if os.environ.get("KIROCUT_NO_REOPEN"):
        return False
    try:
        if os_name == "Darwin":   # osascript returns once Terminal has the window, non-zero when it is refused
            return subprocess.run(argv, capture_output=True, timeout=60).returncode == 0
        if os_name == "Windows":
            subprocess.Popen(argv, cwd=str(folder), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10))
            return True
        p = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:   # a terminal that cannot start exits at once
            return p.wait(timeout=2) == 0
        except subprocess.TimeoutExpired:
            return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def open_claude(folder, prompt, os_name=None, run=start, session=None, resume=False):
    """(opened, the command as the user would type it, for the page to show when nothing opened).
    The terminal starts in this repo so `.kiro/skills` load. `folder` is the video or library the job is about;
    KIROCUT_LIBRARY, when set, is passed through so Kiro finds those videos.
    session: resume=True carries that conversation on.
    run(argv, folder, os_name) -> bool; the demos pass a recorder so no real window opens."""
    os_name = os_name or platform.system()
    here = workspace()
    cmd = plan(os_name, prompt=prompt, session=session, resume=resume)
    # a Terminal opened by osascript does not inherit the window's folders, so the new Kiro would
    # listen on another home. Windows and x-terminal-emulator start as children and inherit them.
    pairs = [f"{k}={os.environ[k]}" for k in ("KIROCUT_HOME", "KIROCUT_LIBRARY") if os.environ.get(k)]
    if pairs and os_name != "Windows":
        cmd = ["env", *pairs] + cmd
    text = (f"cd /d {show([str(here)], os_name)} && " if os_name == "Windows" else f"cd {show([str(here)], os_name)} && ") \
        + show(cmd, os_name)
    argv = terminal(here, cmd, os_name)
    return (bool(argv) and run(argv, here, os_name)), text


def type_into(tty, text, os_name=None, run=None):
    """Type text and Enter into the Terminal tab on that tty (a Claude Code already open there takes it as a
    message). True when a Terminal tab had that tty. Terminal.app only: other apps cannot be typed into from here."""
    if (os_name or platform.system()) != "Darwin" or not tty or run is None and os.environ.get("KIROCUT_NO_REOPEN"):
        return False
    q = lambda x: str(x).replace("\\", "\\\\").replace('"', '\\"')
    script = (f'tell application "Terminal"\nrepeat with w in windows\nrepeat with t in tabs of w\n'
              f'if tty of t is "{q(tty)}" then\ndo script "{q(text)}" in t\nreturn "typed"\nend if\n'
              f'end repeat\nend repeat\nend tell\nreturn ""')
    try:
        out = (run or (lambda a: subprocess.run(a, capture_output=True, text=True, timeout=20).stdout))(["osascript", "-e", script])
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "typed" in (out or "")


def show_tab(tty, os_name=None, run=None):
    """Bring the Terminal tab on that tty to the front (the page's Show Claude). True when a Terminal tab had it.
    Terminal.app only, like type_into."""
    if (os_name or platform.system()) != "Darwin" or not tty or run is None and os.environ.get("KIROCUT_NO_REOPEN"):
        return False
    q = lambda x: str(x).replace("\\", "\\\\").replace('"', '\\"')
    script = (f'tell application "Terminal"\nrepeat with w in windows\nrepeat with t in tabs of w\n'
              f'if tty of t is "{q(tty)}" then\nset selected of t to true\nset index of w to 1\nactivate\nreturn "shown"\nend if\n'
              f'end repeat\nend repeat\nend tell\nreturn ""')
    try:
        out = (run or (lambda a: subprocess.run(a, capture_output=True, text=True, timeout=20).stdout))(["osascript", "-e", script])
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "shown" in (out or "")


def connect(folder, now=None):
    """The page's "Connect Claude" and kirocut: a new terminal running Claude with LISTEN, one at a time.
    (status, command to copy): "listening" (one already is), "pending" (one opened under CONNECT_S ago),
    "opened", or "manual" (no terminal opened: the command is for the user to run)."""
    if home.listening():
        return "listening", ""
    now = now or time.time()

    def claim(d):
        if now - (d.get("connect") or 0) < CONNECT_S:
            return False
        d["connect"] = now   # the page reads it; home.py wait clears it once Claude listens
        return True
    if not home.update(claim):
        return "pending", ""
    opened, text = open_claude(folder, LISTEN)
    if not opened:
        home.update(lambda d: d.pop("connect", None))
    return ("opened" if opened else "manual"), text


CONNECTED = {"listening": "Kiro is already listening.", "pending": "Kiro is already starting in another Terminal window.",
             "opened": "Kiro is starting in a new Terminal window. It picks up what you make in the window."}


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    dry, window_only = "--dry-run" in a, "--window-only" in a
    os_name = a[a.index("--os") + 1] if "--os" in a else platform.system()
    lib = library.path(make=not dry)
    url = home.running()
    if url:
        print(f"Opening your editor...\n  Already open at {url.split('?')[0]}")
        if not dry:
            webbrowser.open(url)
        if not window_only:
            st, text = ("listening" if home.listening() else "opened", "") if dry else connect(lib)
            print("  " + CONNECTED.get(st, f"Run this in a new Terminal window so Kiro picks up your jobs:\n  {text}"))
        return 0
    if window_only:   # the page alone, served from this terminal; jobs wait until a Claude listens
        serve = [sys.executable, str(Path(home.__file__)), "serve"]
        if dry:
            print(show(serve, os_name))
            return 0
        print("Opening your editor...\n  Window only: Kiro is not started. Keep this terminal open while you use it.", flush=True)
        return subprocess.call(serve)
    cmd = plan(os_name)
    here = workspace()
    if dry:
        print(f"cd {show([str(here)], os_name)}\n{show(cmd, os_name)}")
        return 0
    if not shutil.which(cmd[0]) and not Path(cmd[0]).is_file():
        print("The Kiro CLI is not installed yet. Install it from https://kiro.dev/docs/getting-started/installation/, then run this again.")
        return 1
    print(f"Opening your editor...\n  Your videos: {lib}\n  Kiro is starting. The window opens in a moment.\n"
          "  If Kiro asks whether you trust this folder, press the down arrow to pick \"Yes, I trust this folder\",\n"
          "  then Enter (Enter alone picks \"No, exit\"). It is this project folder.",
          flush=True)
    os.chdir(here)
    if os_name == "Windows":
        return subprocess.call(cmd)
    os.execvp(cmd[0], cmd)   # hand the terminal to Claude Code


def demo():
    global open_claude
    import contextlib
    import io
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="launcher_demo_"))
    os.environ["KIROCUT_HOME"] = str(tmp / "home")
    os.environ["KIROCUT_LIBRARY"] = str(tmp / "My Videos")
    for os_name in ("Darwin", "Linux", "Windows"):
        cmd = plan(os_name, plugin=Path("/repo/plugins/kirocut"), exe="kiro-cli")
        assert cmd[:2] == ["kiro-cli", "chat"] and cmd[-1] == PROMPT, cmd
        assert "--trust-all-tools" not in cmd and "--plugin-dir" not in cmd, cmd
        assert not any("dangerously" in c or "bypass" in c.lower() for c in cmd), "never bypass permissions"
        resumed = plan(os_name, exe="kiro-cli", session="abc")
        assert resumed[2:4] == ["--resume-id", "abc"] and resumed[-1] == PROMPT, resumed
        o = io.StringIO()
        with contextlib.redirect_stdout(o):
            assert main(["--dry-run", "--os", os_name]) == 0
        lines = o.getvalue().splitlines()
        q = '"' if os_name == "Windows" else "'"
        assert lines[0].startswith("cd ") and str(workspace()) in lines[0] and lines[1].endswith(f"{q}{PROMPT}{q}"), lines
        print(f"{os_name:<8} {lines[0]}  &&  {lines[1]}")
    assert not (tmp / "My Videos").exists(), "a dry run makes nothing"
    # a Claude of its own for a new video: the window it would open, per OS (recorded, never run)
    for os_name in ("Darwin", "Windows", "Linux"):
        ran = []
        opened, text = open_claude(Path("/lib/My Videos"), "/kirocut:start take job video-2", os_name,
                                   run=lambda w, f, o: ran.append((w, f)) or True)
        assert "take job video-2" in text and (os_name == "Windows" or "My Videos" in text), text
        assert str(workspace()) in text, text
        if ran:
            assert opened and len(ran) == 1
            w, f = ran[0]
            flat = w if isinstance(w, str) else " ".join(w)
            assert "take job video-2" in flat and (os_name == "Windows" or "My Videos" in flat), flat
            assert os_name != "Darwin" or w[0] == "osascript", w
            assert os_name != "Windows" or (w.startswith('cmd /k "') and text.startswith("cd /d ")), (w, text)
        else:
            assert os_name == "Linux" and not opened and not shutil.which("x-terminal-emulator"), "no terminal: copy it"
        print(f"{os_name:<8} new Kiro: {text}")
        assert open_claude(Path("/lib/My Videos"), "x", os_name, run=lambda w, f, o: False)[0] is False, "nothing opened"
    # a page already served: its address opens again, Claude Code is not started a second time
    opened, real = [], (home.running, webbrowser.open)
    home.running, webbrowser.open = (lambda: "http://127.0.0.1:47821/?t=x"), opened.append
    try:
        o = io.StringIO()
        with contextlib.redirect_stdout(o):
            assert main(["--window-only"]) == 0   # Claude's side is checked below, with the terminal faked
        assert opened == ["http://127.0.0.1:47821/?t=x"] and "Already open at http://127.0.0.1:47821/" in o.getvalue()
        assert "t=x" not in o.getvalue(), "the token is not printed"
    finally:
        home.running, webbrowser.open = real
    # "Connect Claude": the start prompt and the narrow settings layer, one terminal at a time (recorded, never run)
    real_open, ran = open_claude, []
    open_claude = lambda f, p: real_open(f, p, "Darwin", run=lambda w, fo, o: ran.append(w) or True)
    try:
        st, text = connect(tmp)
        assert st == "opened" and len(ran) == 1 and text.endswith(shlex.quote(LISTEN)), (st, text)
        script = ran[0][2]   # osascript -e '<the Terminal script>'
        assert LISTEN in script and "chat" in script and "--trust-all-tools" not in script and "Bash(*)" not in script, script
        os.environ["KIROCUT_HOME"] = str(tmp / "home")
        assert " && env " + shlex.quote(f"KIROCUT_HOME={tmp / 'home'}") + " " in open_claude(tmp, LISTEN)[1], "the new Kiro uses the window's home"
        assert "dangerously" not in script and "bypass" not in script.lower(), "never bypass permissions"
        ran.clear()
        assert connect(tmp) == ("pending", "") and not ran, "no second terminal while one is pending"
        assert connect(tmp, now=time.time() + CONNECT_S + 1)[0] == "opened" and len(ran) == 1, "retry after the minute"
        home.update(lambda d: d.pop("connect", None))
        (home.home() / ".listening").write_text("sess-A", encoding="utf-8")
        ran.clear()
        assert connect(tmp) == ("listening", "") and not ran, "one is listening: nothing opens"
        # kirocut with the window open: Claude only when nobody listens, never with --window-only
        home.running, webbrowser.open = (lambda: "http://127.0.0.1:47821/?t=x"), (lambda u: None)
        for args, listen, want, n in (([], True, "already listening", 0), (["--window-only"], False, None, 0),
                                       ([], False, "starting in a new Terminal", 1)):
            home.update(lambda d: d.pop("connect", None))
            (home.home() / ".listening").unlink(missing_ok=True)
            if listen:
                (home.home() / ".listening").write_text("sess-A", encoding="utf-8")
            ran.clear()
            o = io.StringIO()
            with contextlib.redirect_stdout(o):
                assert main(args) == 0
            assert len(ran) == n and (want in o.getvalue() if want else "Claude" not in o.getvalue()), (args, o.getvalue())
        o = io.StringIO()
        home.running = lambda: None
        with contextlib.redirect_stdout(o):
            assert main(["--window-only", "--dry-run"]) == 0
        assert o.getvalue().strip().endswith("home.py serve") and "--settings" not in o.getvalue(), o.getvalue()
        print("connect  ok: start prompt, narrow Allow rules, one at a time, --window-only")
        if os.name != "nt":   # kirocut runs the newest version folder, not the one it was installed from
            b = Path(tmp) / ".kiro/powers/kirocut"
            for v in ("2.4.0", "2.10.0", "2.9.9-3efeb61"):
                (b / v / "lib/kirocut").mkdir(parents=True)
                (b / v / "lib/kirocut/launcher.py").write_text(f"print('ran {v}')", encoding="utf-8")
            f = Path(tmp) / "ne"
            f.write_text(launcher_text("Linux", b / "2.4.0/lib/kirocut/launcher.py"), encoding="utf-8")
            out = subprocess.run(["sh", str(f)], capture_output=True, text=True).stdout.strip()
            assert out == "ran 2.10.0", out
            print("newest   ok: kirocut runs the newest installed version")
    finally:
        open_claude, (home.running, webbrowser.open) = real_open, real
    shutil.rmtree(tmp, ignore_errors=True)
    print("launcher demo ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["demo"]:
        demo()
    else:
        sys.exit(main())
