"""Jobs and the review loop: render in the background with progress, hand a draft back to the user's page, answer notes.

Long work (a render) runs as a detached job (jobs.py): kirocut_render returns a job id at once and kirocut_job reports it, waiting
and streaming progress when asked. The review commands (round, resolve, status, final) are review.py's own functions called
in-process, so their rules still hold (a round is refused while notes are unanswered, a Stop on the page stops the round).
"""
import argparse
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

import jobs
from server import ToolError, PLUGIN
from tools import lazy, resolve_edit

SCENE_PY = PLUGIN / "lib" / "kirocut" / "scene.py"
EDIT_PY = PLUGIN / "skills" / "style-edit" / "scripts" / "edit.py"
EDIT = {"type": "string", "description": "The edit: its folder, or its name in the library"}


def run_cli(fn, *args):
    """Call a CLI function of review.py or home.py in-process: (what it printed, what it returned). Its sys.exit(message) becomes a
    ToolError with a code the agent can act on (stopped, refused, failed)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            ret = fn(*args)
    except SystemExit as e:
        text = (buf.getvalue() + "\n" + (e.code if isinstance(e.code, str) else "")).strip()
        code = "stopped" if "STOPPED" in text else "refused" if "REFUSED" in text else "failed"
        hint = {"stopped": "Stop what you are doing, say so in one line, and call kirocut_events.",
                "refused": "Do what the message says, then call this again.", "failed": ""}[code]
        raise ToolError(code, text or f"exited with {e.code}", hint)
    return buf.getvalue().strip(), ret


def mark_working(review, folder, cmd):
    """What review.py's command line does before every command: this agent is on this edit now (the page's Kiro control and
    where its notes go)."""
    (folder / "review").mkdir(parents=True, exist_ok=True)
    sid = os.environ.get("KIROCUT_SESSION", "")
    review.mark_path(folder, write=True).write_text(json.dumps({"pid": os.getpid(), "session": sid, "kind": "kiro"}), encoding="utf-8")
    if sid:
        (folder / "review" / ".session").write_text(sid, encoding="utf-8")
    review.note_session(folder, cmd)


def review_folder(edit):
    folder = resolve_edit(edit)
    if not (folder / "review.json").is_file():
        raise ToolError("no_review", f"{folder.name} has no review page yet", "review.py start opens it (the cut and style-edit skills do)")
    return folder, lazy("review")


def register(s):
    # ---- renders
    @s.tool("kirocut_render",
            "Start a render in the background and return a job id at once. mode export renders the scene (what the user sees on the page) to an "
            "MP4; mode plan renders the style-edit plan.json (render.mp4, or render-draft.mp4 with draft); mode patch re-renders only the "
            "changed part of render.mp4. Then call kirocut_job with the job id and wait_s to follow it.",
            {"type": "object", "required": ["edit"], "properties": {
                "edit": EDIT, "mode": {"type": "string", "enum": ["export", "plan", "patch"], "description": "default export"},
                "draft": {"type": "boolean", "description": "A smaller, faster render to check the look"},
                "out": {"type": "string", "description": "export: where to write the MP4 (default: the edit's exports folder)"},
                "range": {"type": "string", "description": "patch: seconds like 13-15.5 to re-render"},
                "cloud": {"type": "string", "enum": ["modal", "lambda", "github"], "description": "plan: render in the cloud (the user has set it up)"}}})
    def kirocut_render(ctx, edit, mode="export", draft=False, out=None, range=None, cloud=None):
        folder = resolve_edit(edit)
        if mode == "export":
            if not (folder / "scene.json").is_file():
                raise ToolError("no_scene", f"{folder.name} has no scene.json", "open the edit in the editor first, or use mode plan")
            cmd = [sys.executable, str(SCENE_PY), "render", str(folder)] + (["--draft"] if draft else []) + (["--out", str(out)] if out else [])
            target = out
        elif mode in ("plan", "patch"):
            if not (folder / "plan.json").is_file():
                raise ToolError("no_plan", f"{folder.name} has no plan.json", "the style-edit skill makes it")
            cmd = [sys.executable, str(EDIT_PY), "render" if mode == "plan" else "patch", str(folder)]
            if mode == "plan":
                cmd += (["--draft"] if draft else []) + ([f"--{cloud}"] if cloud else [])
                target = folder / ("render-draft.mp4" if draft else "render.mp4")
            else:
                cmd += (["--range", range] if range else [])
                target = folder / "render.mp4"
        else:
            raise ToolError("bad_arguments", f"unknown mode {mode}", "export, plan or patch")
        job = jobs.start("render", cmd, cwd=folder, edit=folder, out=target)
        job["next"] = "Call kirocut_job with this job_id and wait_s (up to 55) to follow it. Tell the user it has started and about how long."
        return job

    @s.tool("kirocut_job",
            "Follow a background job (a render). With wait_s it waits up to that many seconds for it to end, sending progress as it goes. "
            "With cancel it stops it. With no job_id it lists recent jobs. The window's Stop button also cancels the running job.",
            {"type": "object", "properties": {
                "job_id": {"type": "string"}, "wait_s": {"type": "number", "description": "Seconds to wait for it to end (0 to 55)"},
                "cancel": {"type": "boolean"}}})
    def kirocut_job(ctx, job_id=None, wait_s=0, cancel=False):
        if not job_id:
            return {"jobs": jobs.list_jobs(10)}
        if jobs.get(job_id) is None:
            raise ToolError("no_such_job", f"no job {job_id}", "call kirocut_job with no job_id to list them")
        if cancel:
            return jobs.cancel(job_id)
        import kirohook
        end, last = time.time() + min(max(float(wait_s), 0.0), 55.0), None
        while True:
            v = jobs.get(job_id)
            if v["state"] in ("done", "failed", "cancelled"):
                break
            if kirohook.stopped():   # the user pressed Stop in the window
                v = jobs.cancel(job_id)
                v["stopped_by_user"] = True
                break
            if v["progress_pct"] is not None and v["progress_pct"] != last:
                last = v["progress_pct"]
                ctx.progress(last, 100, v["last_line"][:80])
            if time.time() >= end or ctx.cancelled.is_set():
                break
            time.sleep(1.0)
        if v["state"] == "done" and not v.get("output"):   # a script that prints where it wrote the file
            p = Path(v["last_line"]) if v["last_line"] else None
            v["output"] = str(p) if p and p.is_file() else None
        v["next"] = {"running": "Still running: call kirocut_job again, or tell the user the progress.",
                     "done": "Finished. If the user is reviewing on the page, hand the draft back with kirocut_review_round.",
                     "failed": "It failed: read log_tail, fix the cause, or offer the draft or cloud render.",
                     "cancelled": "Cancelled. Say so in one line."}.get(v["state"], "")
        return v

    @s.tool("kirocut_stills",
            "Make still frames of the scene at times (scene seconds) so you can look at the result before rendering. Returns PNG paths; "
            "look at them with your image reading.",
            {"type": "object", "required": ["edit", "at"], "properties": {
                "edit": EDIT, "at": {"type": "array", "items": {"type": "number"}, "description": "1 to 8 times in seconds"},
                "alt": {"type": "string", "description": "A version (trial reel) instead of the main scene"}}}, read_only=True)
    def kirocut_stills(ctx, edit, at, alt=None):
        folder = resolve_edit(edit)
        sc = lazy("scene")
        if not at or len(at) > 8:
            raise ToolError("bad_arguments", "give 1 to 8 times in at", "")
        scene = sc.scene_of(folder, alt)
        out_dir = folder / "stills" / "chat"
        out_dir.mkdir(parents=True, exist_ok=True)
        names = {f"t{t:g}".replace(".", "_"): min(int(round(float(t) * scene["fps"])), max(0, int(scene["duration"] * scene["fps"]) - 1)) for t in at}
        import subprocess
        cmd = [sys.executable, str(SCENE_PY), "stills", str(folder), str(out_dir)] + [f"{k}={v}" for k, v in names.items()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode:
            raise ToolError("stills_failed", (r.stderr or r.stdout).strip()[-400:], "the renderer may not be installed: run kirocut_status")
        files = [str(out_dir / f"{k}.png") for k in names if (out_dir / f"{k}.png").is_file()]
        return {"stills": files, "times": [float(t) for t in at]}

    # ---- the window's jobs
    @s.tool("kirocut_report",
            "Report progress on a job you took from the editor window (a JOB line from kirocut_events) so its card shows the step, a "
            "detail, a progress number, and finally done or failed. job is the job type from the JOB line (video, teardown, setup...).",
            {"type": "object", "required": ["job"], "properties": {
                "job": {"type": "string"}, "step": {"type": "string", "description": "What you are doing now, a short sentence"},
                "detail": {"type": "string"}, "progress": {"type": "number", "description": "0 to 1"},
                "result": {"type": "object", "description": "Result fields for the card (path, links...)"},
                "done": {"type": "boolean"}, "failed": {"type": "string", "description": "Why it failed, one sentence"}}})
    def kirocut_report(ctx, job, step=None, detail=None, progress=None, result=None, done=False, failed=None):
        home = lazy("home")
        if job not in home.JOBS:
            raise ToolError("bad_arguments", f"unknown job type {job}", "one of: " + ", ".join(home.JOBS))
        ns = argparse.Namespace(job=job, step=step, detail=detail, progress=progress, result=json.dumps(result) if result else None,
                                done=bool(done), failed=failed, if_active=False, key=None)
        text, code = run_cli(home.cmd_status, ns)
        return {"ok": code in (None, 0), "line": text.splitlines()[-1] if text else ""}

    # ---- the review loop
    @s.tool("kirocut_review_round",
            "Hand a draft back to the user's review page as the next round, after you answered their notes. With scene true (default) "
            "the notes were answered in the scene: no render. Otherwise give video, a new render. Refused while any note of the round is "
            "unanswered: resolve each first with kirocut_review_resolve. After this, call kirocut_events to wait for their next move.",
            {"type": "object", "required": ["edit"], "properties": {
                "edit": EDIT, "stage": {"type": "string", "enum": ["cut", "edit"]}, "scene": {"type": "boolean", "description": "default true"},
                "video": {"type": "string", "description": "A new render, when scene is false"},
                "note": {"type": "string", "description": "One line the page shows on the new round"},
                "changed": {"type": "array", "items": {"type": "string"}, "description": "Changes beyond the notes, one line each"},
                "stills": {"type": "boolean", "description": "The video is the stills before the render (approve means render)"},
                "alt": {"type": "string", "description": "The version the notes were on (a trial reel)"}}})
    def kirocut_review_round(ctx, edit, stage=None, scene=True, video=None, note=None, changed=None, stills=False, alt=None):
        folder, review = review_folder(edit)
        mark_working(review, folder, "round")
        a = argparse.Namespace(stage=stage, scene=bool(scene) and not video, video=video, transcript=None, plan=None, note=note, name=None,
                               changed=changed, stills=bool(stills), alt=alt)
        if a.stage == "edit":
            for k, f in (("transcript", "words.json"), ("plan", "plan.json")):
                if (folder / f).exists():
                    setattr(a, k, str(folder / f))
        text, _ = run_cli(review.cmd_round, a, folder)
        return {"round": text, "next": "Now call kirocut_events and wait for the user's reply on the page."}

    @s.tool("kirocut_review_resolve",
            "Mark one of the user's notes fixed, wontfix or open, with one line saying what you did (the page shows it next to the note).",
            {"type": "object", "required": ["edit", "id", "status"], "properties": {
                "edit": EDIT, "id": {"type": "integer"}, "status": {"type": "string", "enum": ["fixed", "wontfix", "open"]},
                "reply": {"type": "string"}, "new_t": {"type": "number", "description": "Where the note's moment is now, in seconds"}}})
    def kirocut_review_resolve(ctx, edit, id, status, reply=None, new_t=None):
        folder, review = review_folder(edit)
        mark_working(review, folder, "resolve")
        text, _ = run_cli(review.cmd_resolve, argparse.Namespace(id=int(id), status=status, reply=reply, new_t=new_t), folder)
        return {"result": text}

    @s.tool("kirocut_review_status",
            "Tell the user's page what you are doing for the next round (one line, or one of the edit's steps: captions, visuals, plan, "
            "render), so they see progress instead of silence. done true closes it.",
            {"type": "object", "required": ["edit"], "properties": {
                "edit": EDIT, "text": {"type": "string"}, "step": {"type": "string", "enum": ["captions", "visuals", "plan", "render"]},
                "log": {"type": "string", "description": "A render log whose last N/M becomes the progress bar"}, "done": {"type": "boolean"}}})
    def kirocut_review_status(ctx, edit, text="", step=None, log=None, done=False):
        folder, review = review_folder(edit)
        mark_working(review, folder, "status")
        out, _ = run_cli(review.cmd_status, argparse.Namespace(text=text, step=step, log=log, done=bool(done)), folder)
        return {"result": out}

    @s.tool("kirocut_review_final",
            "Say the cut is the finished video: no styled edit follows its Approve ('just the cut').",
            {"type": "object", "required": ["edit"], "properties": {"edit": EDIT}})
    def kirocut_review_final(ctx, edit):
        folder, review = review_folder(edit)
        mark_working(review, folder, "final")
        run_cli(review.cmd_final, folder)
        return {"final": True}
