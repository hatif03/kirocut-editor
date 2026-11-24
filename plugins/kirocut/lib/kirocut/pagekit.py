#!/usr/bin/env python3
"""What the window (home.py) and the review page (review.py) share about a request and its pictures. Stdlib only.

    same_origin(handler)            a POST from the page itself, not from another site's page
    save_images(folder, imgs, prefix, keep=())   pictures pasted, dropped or picked on a page, saved into folder
    session()                       the chat session this process works for (KIROCUT_SESSION, set by the MCP server)
    agent_env()                     {session, kind: "kiro"} when a Kiro chat runs this, else {}
    home_dir()                      $KIROCUT_HOME, else ~/.kirocut

    python3 pagekit.py demo
"""
import base64
import os
import re
import sys
from pathlib import Path

MAX_IMAGE = 15 << 20      # an attached image (review notes, a new video's pictures)
MAX_IMAGES = 6
MAX_BODY = MAX_IMAGES * MAX_IMAGE * 4 // 3 + (1 << 20)   # a POST carrying that many, base64


def home_dir():
    return Path(os.environ.get("KIROCUT_HOME", "").strip() or Path.home() / ".kirocut")


def session():
    """The Kiro chat this process works for, or "". The MCP server sets KIROCUT_SESSION for every command it runs."""
    return os.environ.get("KIROCUT_SESSION", "").strip()


def agent_env(env=None):
    """{session, host_session, kind} of the Kiro chat running this command, or {} outside one."""
    env = os.environ if env is None else env
    sid = env.get("KIROCUT_SESSION", "").strip()
    return {"session": sid, "host_session": "", "kind": "kiro"} if sid else {}


def same_origin(h):
    """A POST from the page itself: no Origin header (curl, a script) or this server's own address."""
    o = h.headers.get("Origin")
    return not o or o == "http://" + (h.headers.get("Host") or "")


def save_images(folder, imgs, prefix, keep=()):
    """Attached pictures: names already kept (keep) and pasted, dropped or picked data urls (saved into folder).
    Only png, jpeg, gif and webp, under MAX_IMAGE each, at most MAX_IMAGES. The saved names, in order."""
    out = []
    for im in imgs:
        if len(out) == MAX_IMAGES or not isinstance(im, str):
            continue
        if im in keep:
            out.append(im)
            continue
        m = re.match(r"data:image/(png|jpeg|gif|webp);base64,(.+)", im, re.S)
        if not m:
            continue
        try:
            raw = base64.b64decode(m[2])
        except ValueError:
            continue
        if len(raw) > MAX_IMAGE:
            continue
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        k = 1
        while any((folder / f"{prefix}-img{k}.{x}").exists() for x in ("jpg", "png", "gif", "webp")):
            k += 1
        name = f"{prefix}-img{k}.{'jpg' if m[1] == 'jpeg' else m[1]}"
        (folder / name).write_bytes(raw)
        out.append(name)
    return out


def demo():
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="pagekit_demo_"))
    png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n").decode()
    got = save_images(d, [png, "data:text/html;base64,PGI+", png, "kept.png"], "n1", keep=("kept.png",))
    assert got == ["n1-img1.png", "n1-img2.png", "kept.png"] and (d / "n1-img1.png").read_bytes() == b"\x89PNG\r\n", got
    assert len(save_images(d, [png] * 9, "n2")) == MAX_IMAGES
    assert agent_env({}) == {} and agent_env({"KIROCUT_SESSION": "kiro-1"}) == {"session": "kiro-1", "host_session": "", "kind": "kiro"}

    class H:
        headers = {"Host": "127.0.0.1:5"}
    assert same_origin(H)
    H.headers = {"Host": "127.0.0.1:5", "Origin": "http://127.0.0.1:5"}
    assert same_origin(H)
    H.headers = {"Host": "127.0.0.1:5", "Origin": "https://evil.example"}
    assert not same_origin(H)
    print("pagekit demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
