"""Every KiroCut tool, registered on the server. Each tool is a thin wrapper over the plugin's own
modules (scene.py, review.py, home.py, library.py, taste.py), imported in-process and called as functions,
so a tool returns data, not a command's text. Modules load on first use: the server starts fast and a
broken optional module breaks only the tools that need it.
"""
import importlib
import importlib.util
import os
import platform
import sys
import time
from pathlib import Path

from server import ToolError, PLUGIN, VERSION

SETUP_PY = PLUGIN / "skills" / "setup" / "scripts" / "setup.py"


def lazy(name):
    """A plugin module by name (lib/kirocut is on sys.path), or a ToolError the agent can read."""
    try:
        return importlib.import_module(name)
    except Exception as e:   # noqa: BLE001
        raise ToolError("module_unavailable", f"could not load {name}: {type(e).__name__}: {e}",
                        "run kirocut_status and fix what it lists, or run the setup skill")


_SETUP = []


def setup_module():
    if not _SETUP:
        spec = importlib.util.spec_from_file_location("kirocut_setup", SETUP_PY)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _SETUP.append(m)
    return _SETUP[0]


def doctor_rows():
    """setup.py's checks as dicts: {name, ok, detail, fix}. Also the extra rows the doctor prints."""
    try:
        rows = setup_module().checks()
    except Exception as e:   # noqa: BLE001
        raise ToolError("doctor_failed", f"the setup check could not run: {e}", f"run: py \"{SETUP_PY}\" doctor")
    return [{"name": n, "ok": bool(ok), "detail": d, "fix": f} for n, ok, d, f in rows]


EDIT_FILES = ("scene.json", "review.json", "plan.json", "cut.mp4", "report.json", "spans.json", "style.json")


def resolve_edit(edit):
    """An edit folder from what the agent gave: a path (absolute, or relative to the library or the workspace) or a
    name that one library edit has. ToolError listing the choices when it is missing or ambiguous."""
    if not edit or not str(edit).strip():
        raise ToolError("missing_edit", "which edit? give its folder or name", "call kirocut_library to list the edits")
    raw = str(edit).strip()
    lib = lazy("library")
    cands = [Path(raw).expanduser(), lib.path(make=False) / raw, Path.cwd() / raw]
    for c in cands:
        if c.is_dir() and any((c / f).exists() for f in EDIT_FILES) or c.is_dir() and c.parent.name in getattr(lib, "KINDS", ()):
            return c.resolve()
    named = [Path(d) for d in (lib.edit_dirs() or []) if Path(d).name == Path(raw).name]
    if len(named) == 1:
        return named[0].resolve()
    if named:
        raise ToolError("ambiguous_edit", f"{len(named)} edits are called {raw}", "give the full folder: " + "; ".join(str(n) for n in named[:5]))
    raise ToolError("no_such_edit", f"no edit {raw}", "call kirocut_library to list the edits")


def home_state():
    """The editor window's address, or None when it is not served."""
    try:
        return lazy("home").running()
    except ToolError:
        return None


SYSTEM = ("python", "ffmpeg", "node", "git")   # installed by the user (a package manager, a password, a new terminal)
SELF = ("python packages", "transcription model", "renderer", "motion clips")   # setup.py install-all installs these alone


def first_run_setup(rows):
    """What a first run starts by itself: install-all as a background job once the system tools are there (a second call
    finds the running job instead of starting another). The system tools come back as fixes for the user's terminal."""
    import jobs
    missing_sys = [r for r in rows if r["name"] in SYSTEM and not r["ok"]]
    if missing_sys:
        return {"setup": "needs_you", "next": "Ask the user to run each fix in their own terminal (" + ", ".join(r["name"] for r in missing_sys)
                + "), then restart Kiro so the new tools are on its PATH, and call kirocut_status again. KiroCut installs the rest itself."}
    if not any(r["name"] in SELF and not r["ok"] for r in rows):
        return {}
    running = next((j for j in jobs.list_jobs(20) if j.get("kind") == "setup" and j.get("state") in ("starting", "running")), None)
    if not running:
        setup_py = PLUGIN / "skills" / "setup" / "scripts" / "setup.py"
        running = jobs.start("setup", [sys.executable, str(setup_py), "install-all", "--report"], cwd=str(PLUGIN))
    return {"setup": "installing", "setup_job": running["job_id"],
            "next": "KiroCut is installing its Python packages, the speech model and the renderer (about 5-10 minutes, once). Tell the "
                    "user, open the editor (kirocut_open_editor) so they can start meanwhile, and follow it with kirocut_job."}


def register(s):
    @s.tool("kirocut_status",
            "What state KiroCut is in: which tools are installed (ready or a fix command for each), the library folder, "
            "whether the editor window is open and its address, and events waiting from the window. Call this first in a session.",
            {"type": "object", "properties": {"doctor": {"type": "boolean", "description": "Run the tool checks (a few seconds). Default true."},
                                              "auto_setup": {"type": "boolean", "description": "On a first run, start installing what KiroCut can "
                                                             "install itself (Python packages, the speech model, the renderer) as a background "
                                                             "job. Default true."}}})
    def kirocut_status(ctx, doctor=True, auto_setup=True):
        lib = lazy("library")
        out = {"version": VERSION, "platform": platform.system(), "python": platform.python_version(),
               "plugin": str(PLUGIN), "library": str(lib.path(make=False)),
               "kirocut_home": str(lib.home())}
        if doctor:
            rows = doctor_rows()
            out["tools"] = rows
            out["ready"] = all(r["ok"] for r in rows if r["name"] in ("python", "ffmpeg", "node", "python packages", "renderer"))
            out["fixes"] = [r["fix"] for r in rows if not r["ok"] and r["fix"]]
            if not out["ready"] and auto_setup:
                out.update(first_run_setup(rows))
        out["editor_url"] = home_state()
        try:
            from events import pending_count
            out["events_waiting"] = pending_count()
        except Exception:   # noqa: BLE001  the event queue arrives with the editor tools
            out["events_waiting"] = 0
        out["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return out

    for mod in ("tools_read", "tools_scene", "tools_editor", "tools_ask", "tools_jobs"):
        p = Path(__file__).with_name(mod + ".py")
        if p.exists():
            importlib.import_module(mod).register(s)
