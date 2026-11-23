#!/usr/bin/env python3
"""Self-check for the KiroCut tools, through the real server process. Needs ffmpeg (as the other demos do).

    python3 test_tools.py             same as the tool part of `server.py demo`
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib" / "kirocut"))
sys.path.insert(0, str(HERE.parent / "lib"))
from test_server import Client  # noqa: E402


def make_edit(root, name="demo-edit"):
    """An edit folder with a 6 s test clip as two clips, a text and captions: the same sample the scene demo builds."""
    import scene
    e = Path(root) / "edits" / name
    e.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x568:r=30:d=6", "-f", "lavfi", "-i", "sine=d=6",
                    "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(e / "take.mp4")], check=True)
    S = scene.Scene(1080, 1920, 30, edit=e)
    S.video("take.mp4", 0, 2, **{"in": 1})
    S.video("take.mp4", 2, 4, **{"in": 3})
    S.text("Hello", 1, 3, y=400)
    S.captions([{"w": "one", "start": 1.2, "end": 1.6}, {"w": "two", "start": 2.0, "end": 2.4}, {"w": "three", "start": 3.4, "end": 3.8}],
               {"y_pct": 70}, asset="take")
    S.save(e)
    return e


def web(url, path="", body=None, headers=None):
    """GET (or POST a JSON body to) a path on a server address that carries ?t=token."""
    import urllib.request
    base, tok = url.split("/?t=", 1)
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"{base}{path}{sep}t={tok}", json.dumps(body).encode() if body is not None else None, headers or {},
                                 method="POST" if body is not None else "GET")
    return urllib.request.urlopen(req, timeout=30)


def editor_demo(c, tmp, e):
    """The window and a review page started by the tools, and what the user does in them reaching kirocut_events."""
    import time
    err, win = c.call("kirocut_open_editor")
    try:
        assert not err and win["kind"] == "home" and win["url"].startswith("http://127.0.0.1:") and win["tier"] == "browser", win
        assert win["embed_url"].endswith("&embed=1") and win["markdown"].startswith("[Open KiroCut]("), win
        err, again = c.call("kirocut_open_editor")
        assert not err and again["url"] == win["url"] and not again["started"], "a second call reuses the window"
        # the user starts something in the window: it is one JOB event, delivered once
        r = web(win["url"], "/job", {"type": "teardown", "handle": "listen", "platform": "youtube"})
        assert r.status == 200
        err, ev = c.call("kirocut_events", wait_s=5)
        assert not err and ev["count"] == 1 and ev["events"][0]["kind"] == "job" and ev["events"][0]["line"].startswith("JOB teardown"), ev
        err, ev = c.call("kirocut_events", wait_s=0)
        assert not err and ev["count"] == 0 and "Nothing yet" in ev["next"], "each event comes once"
        # a review page for the edit: Send notes reaches the chat as one event with the note in it
        subprocess.run([sys.executable, str(HERE.parent / "lib" / "kirocut" / "review.py"), str(e), "start", "--video", str(e / "take.mp4"),
                        "--stage", "cut"], check=True, capture_output=True)
        err, rv = c.call("kirocut_open_editor", edit="demo-edit")
        assert not err and rv["kind"] == "edit" and rv["edit"] == str(e), rv
        web(rv["url"], "/comment", {"t": 1.2, "text": "cut the pause here"})
        web(rv["url"], "/event", {"type": "send"})
        st = json.loads(web(rv["url"], "/state").read())
        assert st["agent_ui"]["state"] in ("waiting", "working", "open") and "ide" not in st, "the page shows the chat's state"
        err, ev = c.call("kirocut_events", wait_s=5)
        assert not err and ev["count"] == 1 and ev["events"][0]["kind"] == "review" and ev["events"][0]["type"] == "send", ev
        assert "cut the pause here" in ev["events"][0]["text"], ev["events"][0]["text"]
        assert c.call("kirocut_events", wait_s=0)[1]["count"] == 0
        # answering the notes: a round is refused while one is unanswered, then handed back once resolved
        err, ref = c.call("kirocut_review_round", edit="demo-edit", stage="cut", scene=False, video=str(e / "take.mp4"))
        assert err and ref["code"] == "refused" and "answer every note" in ref["message"], ref
        err, rs = c.call("kirocut_review_resolve", edit="demo-edit", id=1, status="fixed", reply="Cut the pause")
        assert not err and "fixed" in rs["result"], rs
        err, st = c.call("kirocut_review_status", edit="demo-edit", text="Rebuilding the cut")
        assert not err and "Rebuilding the cut" in st["result"], st
        err, rd = c.call("kirocut_review_round", edit="demo-edit", stage="cut", scene=False, video=str(e / "take.mp4"), note="Pause removed")
        assert not err and "round 2" in rd["round"], rd
        assert json.loads(web(rv["url"], "/state").read())["round"] == 2, "the user's page is on round 2"
        # while kirocut_events waits the pages say Kiro is listening, and stop saying so when it returns
        import threading
        seen = []
        t = threading.Thread(target=lambda: seen.append(c.call("kirocut_events", wait_s=3)))
        t.start()
        time.sleep(1.2)
        assert json.loads(web(rv["url"], "/state").read())["agent_ui"]["state"] == "waiting", "listening while it waits"
        t.join()
        assert json.loads(web(rv["url"], "/state").read())["agent_ui"]["state"] != "waiting"
        err, bad = c.call("kirocut_open_editor", edit="nope")
        assert err and bad["code"] == "no_such_edit"
        print("editor   ok: window and review page started once, jobs and notes arrive exactly once, listening light")
    finally:   # the servers the tools started live on their own: end exactly those
        import tools_editor
        tools_editor.stop_servers(tmp / "home" / "home" / "server.pid", tmp / "home" / "server.pid", e / "review" / "server.pid")


def jobs_demo(env):
    """Background jobs: progress from a log, a failure with its log tail, a cancel, and Stop from the window."""
    import jobs
    import time
    py = sys.executable
    fast = jobs.start("render", [py, "-c", "import time\nfor i in range(1,5):\n print(f'Rendered {i*25}/100', flush=True); time.sleep(0.4)\nprint('x')"])
    assert fast["state"] in ("starting", "running") and fast["job_id"].startswith("render-"), fast
    with Client(env=env) as c:
        seen = []
        c.rpc("ping")
        err, v = c.call("kirocut_job", job_id=fast["job_id"], wait_s=30)
        assert not err and v["state"] == "done" and v["next"].startswith("Finished"), v
        # a failing command: the log tail says why
        bad = jobs.start("render", [py, "-c", "import sys; print('no such renderer'); sys.exit(3)"])
        err, v = c.call("kirocut_job", job_id=bad["job_id"], wait_s=30)
        assert not err and v["state"] == "failed" and v["exit"] == 3 and "no such renderer" in v["log_tail"][-1], v
        # a long one is cancelled, its whole tree
        slow = jobs.start("render", [py, "-c", "import time\nprint('Rendered 10/100', flush=True)\ntime.sleep(120)"])
        time.sleep(1.5)
        err, v = c.call("kirocut_job", job_id=slow["job_id"], wait_s=1)
        assert not err and v["state"] == "running" and v["progress_pct"] == 10, v
        t0 = time.time()
        err, v = c.call("kirocut_job", job_id=slow["job_id"], cancel=True)
        assert not err and v["state"] == "cancelled" and time.time() - t0 < 10, v
        # the window's Stop (a fresh stop file) cancels the running job a wait is following
        slow2 = jobs.start("render", [py, "-c", "import time; time.sleep(120)"])
        time.sleep(1.0)
        sd = Path(env["KIROCUT_HOME"]) / "stop"
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "s1").write_text("x", encoding="utf-8")
        err, v = c.call("kirocut_job", job_id=slow2["job_id"], wait_s=10)
        assert not err and v["state"] == "cancelled" and v.get("stopped_by_user"), v
        (sd / "s1").unlink()
        err, lst = c.call("kirocut_job")
        assert not err and len(lst["jobs"]) >= 4, lst
        err, bad = c.call("kirocut_job", job_id="nope")
        assert err and bad["code"] == "no_such_job"
        err, bad = c.call("kirocut_render", edit="demo-edit", mode="plan")
        assert err and bad["code"] in ("no_plan", "no_such_edit"), bad
    print("jobs     ok: background job with progress, failure log, cancel, window Stop")


def ask_demo(env):
    """Questions: a form when the IDE can show one, numbered chat text and a parsed reply when it cannot."""
    import tools_ask
    Q = [{"id": "platform", "text": "Where will it be posted?", "options": [{"label": "TikTok (Recommended)"}, {"label": "YouTube Shorts"},
                                                                          {"label": "Instagram Reels"}], "allow_other": True},
         {"id": "extras", "text": "What should the edit add?", "multi": True,
          "options": [{"label": "Captions", "description": "word by word"}, {"label": "Zooms"}, {"label": "Sound effects"}]}]
    qs = tools_ask.clean(Q)
    p = tools_ask.parse_reply
    assert p(qs, "1. 2\n2. 1 and 3") == {"platform": "YouTube Shorts", "extras": ["Captions", "Sound effects"]}
    assert p(qs, "1: youtube\n2: all") == {"platform": "YouTube Shorts", "extras": ["Captions", "Zooms", "Sound effects"]}
    assert p(qs, "1. Threads\n2. none") == {"platform": {"other": "Threads"}, "extras": []}
    assert p(qs[:1], "the first") == {"platform": "TikTok (Recommended)"} and p(qs[:1], "2") == {"platform": "YouTube Shorts"}
    assert p(qs[:1], "the last one") == {"platform": "Instagram Reels"}
    sch = tools_ask.form_schema(qs)
    assert sch["properties"]["platform"]["enum"][1] == "YouTube Shorts" and sch["properties"]["extras__2"]["type"] == "boolean"
    assert all(v["type"] in ("string", "boolean") for v in sch["properties"].values()), "elicitation schemas are flat primitives"
    assert tools_ask.from_form(qs, {"platform": "TikTok (Recommended)", "extras__1": True}) == \
        {"platform": "TikTok (Recommended)", "extras": ["Zooms"]}
    for bad in ([], [{"id": "a", "text": "t", "options": [{"label": "x"}]}], [{"id": "a", "text": "t", "options": [{"label": "x"}, {"label": "x"}]}]):
        try:
            tools_ask.clean(bad)
            raise AssertionError(bad)
        except Exception as e:
            assert getattr(e, "code", "") == "bad_arguments", e
    # form mode: the fake IDE shows a form and answers it
    seen = []

    def ide(req):
        seen.append(req)
        return {"action": "accept", "content": {"platform": "Instagram Reels", "extras__0": True, "extras__2": True}}
    with Client(env=env, caps={"elicitation": {}}) as c:
        c.answer = ide
        err, r = c.call("kirocut_ask", questions=Q)
        assert not err and r["mode"] == "form" and r["answers"] == {"platform": "Instagram Reels", "extras": ["Captions", "Sound effects"]}, r
        assert seen[0]["method"] == "elicitation/create" and "properties" in seen[0]["params"]["requestedSchema"]
        c.answer = lambda req: {"action": "decline"}
        err, r = c.call("kirocut_ask", questions=Q[:1])
        assert not err and r["mode"] == "form" and r["answered"] is False and r["action"] == "decline", r
    # chat mode: no elicitation in the client
    with Client(env=env) as c:
        err, r = c.call("kirocut_ask", questions=Q, intro="Two quick questions.")
        assert not err and r["mode"] == "chat" and "1) TikTok (Recommended)" in r["say_to_user"] and r["say_to_user"].startswith("Two quick"), r
        err, a = c.call("kirocut_answer", ask_id=r["ask_id"], reply="1. 3\n2. 2")
        assert not err and a["answers"] == {"platform": "Instagram Reels", "extras": ["Zooms"]} and not a["unanswered"], a
        err, r2 = c.call("kirocut_ask", questions=[{"id": "pace", "text": "How fast?", "options": [{"label": "Fast"}, {"label": "Calm"}]}])
        err, a = c.call("kirocut_answer", ask_id=r2["ask_id"], reply="hmm not sure")
        assert a["answers"]["pace"] is None and a["unanswered"] == ["pace"] and "Ask again" in a["next"], a
        err, a = c.call("kirocut_answer", ask_id=r2["ask_id"], reply="calm")
        assert a["answers"] == {"pace": "Calm"} and not a["unanswered"], "a label typed out is understood"
        err, bad = c.call("kirocut_answer", ask_id="nope", reply="1")
        assert err and bad["code"] == "no_such_ask"
    print("ask      ok: form (elicitation) and chat fallback, replies parsed, bad questions refused")


def demo():
    if not shutil.which("ffmpeg"):
        print("tools    skipped: ffmpeg not found")
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="mcp_tools_"))
    env = {"KIROCUT_HOME": str(tmp / "home"), "KIROCUT_LIBRARY": str(tmp / "lib"), "KIROCUT_NO_BROWSER": "1"}
    os.environ.update(env)
    e = make_edit(tmp / "lib")
    try:
        with Client(env=env) as c:
            names = {t["name"] for t in c.rpc("tools/list")["result"]["tools"]}
            need = {"kirocut_status", "kirocut_library", "kirocut_taste", "kirocut_scene_show", "kirocut_scene_ops", "kirocut_scene_add",
                    "kirocut_scene_cards", "kirocut_scene_changes", "kirocut_scene_undo"}
            assert need <= names, need - names
            # library: the edit is found by name and by folder
            err, lib = c.call("kirocut_library")
            assert not err and lib["count"] >= 0 and lib["library"] == str(tmp / "lib"), lib
            # scene show: ids, words, pauses, the item at a time
            err, sh = c.call("kirocut_scene_show", edit="demo-edit")
            assert not err and sh["duration"] == 4 and [t["kind"] for t in sh["tracks"]][0] == "visual", sh
            clips = sh["tracks"][0]["items"]
            assert [(x["start"], x["end"], x["in"]) for x in clips] == [(0, 2, 1), (2, 4, 3)], clips
            assert [w["w"] for w in sh["words"]] == ["one", "two", "three"] and sh["pauses"], sh["pauses"]
            err, at = c.call("kirocut_scene_show", edit=str(e), at=1.5)
            assert not err and all(x["start"] <= 1.5 < x["end"] for t in at["tracks"] for x in t["items"]), at
            # trim the first 2 seconds of the footage: the second clip closes up, the text and captions follow the magnet
            err, tr = c.call("kirocut_scene_ops", edit="demo-edit", why="Trim the first second",
                             ops=[{"op": "trim", "item": clips[0]["id"], "edge": "start", "by": 1}])
            assert not err and tr["duration"] == 3 and tr["change"]["n"] == 1 and not tr["through_page"], tr
            sh2 = c.call("kirocut_scene_show", edit="demo-edit")[1]
            assert [(x["start"], x["end"], x["in"]) for x in sh2["tracks"][0]["items"]] == [(0, 1, 2), (1, 3, 3)], sh2["tracks"][0]["items"]
            # add text at 0:02
            err, ad = c.call("kirocut_scene_add", edit="demo-edit", type="text", text="Link in bio", start=2, end=3, why="Add the link")
            assert not err and len(ad["added"]) == 1 and ad["items"][0]["what"] == "Link in bio" and ad["items"][0].get("by") == "kiro", ad
            # the agent's changes are listed, and undoing the first leaves the second
            ch = c.call("kirocut_scene_changes", edit="demo-edit")[1]["changes"]
            assert [x["n"] for x in ch] == [1, 2] and ch[1]["why"] == "Add the link", ch
            err, un = c.call("kirocut_scene_undo", edit="demo-edit", n=1)
            assert not err and un["state"] == "undone" and un["duration"] == 4, un
            sh3 = c.call("kirocut_scene_show", edit="demo-edit")[1]
            assert [(x["start"], x["end"]) for x in sh3["tracks"][0]["items"]] == [(0, 2), (2, 4)]
            assert any(x["what"] == "Link in bio" for t in sh3["tracks"] for x in t["items"]), "the later change stays"
            err, re_ = c.call("kirocut_scene_undo", edit="demo-edit", n=1, redo=True)
            assert not err and re_["duration"] == 3
            # errors are tool errors with a code and a hint, never a crash
            err, bad = c.call("kirocut_scene_ops", edit="demo-edit", why="x", ops=[{"op": "set", "item": "nope", "props": {}}])
            assert err and bad["code"] == "scene_error" and bad["hint"], bad
            err, bad = c.call("kirocut_scene_ops", edit="no-such-edit", why="x", ops=[{"op": "remove", "item": "a"}])
            assert err and bad["code"] == "no_such_edit", bad
            err, bad = c.call("kirocut_scene_ops", edit="demo-edit", why="x", ops=[])
            assert err and bad["code"] == "bad_arguments", bad
            # cut a range out of the footage: across the join of two clips, the gap closes, the rest moves up, the cut is listed
            make_edit(tmp / "lib", "cut-edit")
            err, ct = c.call("kirocut_scene_ops", edit="cut-edit", why="Cut 1.5 to 2.5", ops=[{"op": "cut", "start": 1.5, "end": 2.5}])
            assert not err and ct["duration"] == 3, ct
            sh = c.call("kirocut_scene_show", edit="cut-edit")[1]
            clips = sh["tracks"][0]["items"]
            assert [(x["start"], x["end"], x["in"]) for x in clips] == [(0, 1.5, 1), (1.5, 3, 3.5)], clips
            assert sh["cuts"] == [{"t": 1.5, "clip": clips[1]["id"], "reason": "by hand", "words": "", "dur": 1}], sh["cuts"]
            err, bad = c.call("kirocut_scene_ops", edit="cut-edit", why="x", ops=[{"op": "cut", "start": 2, "end": 9}])
            assert err and bad["code"] == "scene_error" and "footage ends" in bad["message"], bad
            err, bad = c.call("kirocut_scene_ops", edit="cut-edit", why="x", ops=[{"op": "cut", "start": 2, "end": 1}])
            assert err and "before end" in bad["message"], bad
            assert c.call("kirocut_scene_undo", edit="cut-edit")[1]["duration"] == 4, "'undo that': the newest change, a cut is one"
            assert c.call("kirocut_scene_undo", edit="cut-edit", redo=True)[1]["duration"] == 3, "'put it back': the newest undone"
            assert c.call("kirocut_scene_undo", edit="cut-edit", n=1)[1]["duration"] == 4
            err, none = c.call("kirocut_scene_undo", edit="demo-edit", redo=True)
            assert err and none["code"] == "nothing_to_undo", none
            # taste: add, read back, forget
            err, t1 = c.call("kirocut_taste", action="add", section="Captions", rule="captions a bit bigger", setting="captions.size_pct", value=8)
            assert not err and t1["status"] == "added", t1
            got = c.call("kirocut_taste", action="get")[1]
            assert got["settings"]["captions"]["size_pct"] == 8 and got["rules"][0]["rule"] == "captions a bit bigger", got
            err, f = c.call("kirocut_taste", action="forget", id=t1["rule"]["id"])
            assert not err and "size_pct" not in c.call("kirocut_taste", action="get")[1]["settings"].get("captions", {}), f
            print("tools    ok: scene show/ops/add/undo/redo, errors coded, taste add/get/forget, library")
            editor_demo(c, tmp, e)
        ask_demo(env)
        jobs_demo(env)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(demo())
