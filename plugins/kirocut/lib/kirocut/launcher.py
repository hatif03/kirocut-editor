#!/usr/bin/env python3
"""kirocut: open the KiroCut window. Stdlib only.

    kirocut                 open the window (the same address every time); edit by talking to Kiro in the IDE
    kirocut --dry-run       print what it would run
    headless(prompt)        the Kiro CLI with no chat, for a job that must finish on its own (a brand kit, the learn step)
    python3 launcher.py demo   self-check

`setup.py install-launcher` puts the `kirocut` command on the PATH; `uninstall-launcher` takes it off. In the IDE the same
window opens from the chat (the kirocut_open_editor tool). Nothing here starts a chat or opens a terminal: the chat is the
IDE's, and what the user presses in the window reaches it through kirocut_events.
"""
import os
import platform
import shlex
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import home  # noqa: E402
import library  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[2]          # plugins/kirocut
MARK = "installed by kirocut setup.py install-launcher"
# picks the newest version folder next to this one at run time: a power update adds a folder and keeps the old ones
NEWEST = ("import glob,re,sys;d=sys.argv[1];v=lambda p:[int(x) for x in re.findall(r'\\d+',p[len(d):].split('/')[1])[:3]];"
          "print(max(glob.glob(glob.escape(d)+'/*/lib/kirocut/launcher.py'),key=v,default=''))")
TELL = "Talk to Kiro in the IDE chat in your KiroCut folder: say \"edit my video\", or press Make my video here."


def launcher_text(os_name=None, launcher=PLUGIN / "lib" / "kirocut" / "launcher.py", py=sys.executable):
    """The kirocut file. A power install lives in .../kirocut/<version>/: the sh script runs the newest
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
    names = ["kirocut.cmd"] if platform.system() == "Windows" else ["kirocut"]
    dirs = [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p] + [Path.home() / ".local" / "bin"]
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


def headless(prompt, exe=None, os_name=None):
    """The Kiro CLI with no chat, for a job that must finish on its own (a brand kit, the learn step). Permissions stay
    Kiro's: this does not pass --trust-all-tools."""
    os_name = os_name or platform.system()
    exe = exe or shutil.which("kiro-cli") or ("kiro-cli.exe" if os_name == "Windows" else "kiro-cli")
    return [exe, "chat", "--no-interactive", prompt]


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in a
    lib = library.path(make=not dry)
    url = home.running()
    if url:
        print(f"Opening your editor...\n  Already open at {url.split('?')[0]}\n  {TELL}")
        if not dry:
            webbrowser.open(url)
        return 0
    serve = [sys.executable, str(Path(home.__file__)), "serve"]
    if dry:
        print(subprocess.list2cmdline(serve) if os.name == "nt" else shlex.join(serve))
        return 0
    print(f"Opening your editor...\n  Your videos: {lib}\n  {TELL}\n  Keep this terminal open while you use it.", flush=True)
    return subprocess.call(serve)


def demo():
    import contextlib
    import io
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="launcher_demo_"))
    os.environ["KIROCUT_HOME"] = str(tmp / "home")
    os.environ["KIROCUT_LIBRARY"] = str(tmp / "My Videos")
    for os_name in ("Darwin", "Linux", "Windows"):
        cmd = headless("make a brand kit", exe="kiro-cli", os_name=os_name)
        assert cmd == ["kiro-cli", "chat", "--no-interactive", "make a brand kit"], cmd
        assert not any("trust-all" in c or "dangerously" in c or "bypass" in c.lower() for c in cmd), "never bypass permissions"
    o = io.StringIO()
    real = home.running
    home.running = lambda: None
    try:
        with contextlib.redirect_stdout(o):
            assert main(["--dry-run"]) == 0
    finally:
        home.running = real
    assert o.getvalue().strip().endswith("home.py serve"), o.getvalue()
    assert not (tmp / "My Videos").exists(), "a dry run makes nothing"
    # a window already served: its address opens again, nothing else starts, the token is never printed
    opened, real = [], (home.running, webbrowser.open)
    home.running, webbrowser.open = (lambda: "http://127.0.0.1:47821/?t=x"), opened.append
    try:
        o = io.StringIO()
        with contextlib.redirect_stdout(o):
            assert main([]) == 0
        assert opened == ["http://127.0.0.1:47821/?t=x"] and "Already open at http://127.0.0.1:47821/" in o.getvalue(), o.getvalue()
        assert "t=x" not in o.getvalue() and "IDE chat" in o.getvalue()
    finally:
        home.running, webbrowser.open = real
    w = launcher_text("Windows", Path("C:/x/launcher.py"), "C:/py/python.exe")
    assert w.startswith("@echo off\r\n") and MARK in w
    if os.name != "nt":   # kirocut runs the newest version folder, not the one it was installed from
        b = tmp / ".kiro/powers/kirocut"
        for v in ("2.4.0", "2.10.0", "2.9.9-3efeb61"):
            (b / v / "lib/kirocut").mkdir(parents=True)
            (b / v / "lib/kirocut/launcher.py").write_text(f"print('ran {v}')", encoding="utf-8")
        f = tmp / "ne"
        f.write_text(launcher_text("Linux", b / "2.4.0/lib/kirocut/launcher.py"), encoding="utf-8")
        out = subprocess.run(["sh", str(f)], capture_output=True, text=True).stdout.strip()
        assert out == "ran 2.10.0", out
    shutil.rmtree(tmp, ignore_errors=True)
    print("launcher demo ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["demo"]:
        demo()
    else:
        sys.exit(main())
