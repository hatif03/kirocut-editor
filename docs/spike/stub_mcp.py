#!/usr/bin/env python3
"""Throwaway MCP server for the Kiro IDE compatibility spike (docs/KIRO-COMPAT.md). Not shipped.

It reuses KiroCut's real server core, so what works here works for the real tools. Tools:

    spike_info       what the IDE told us at initialize (its name, capabilities), our cwd and argv
    spike_progress   five one-second steps with progress notifications
    spike_elicit     asks the user a question through the client (elicitation)
    spike_page       starts a tiny local page and returns three ways to open it: a command: link to the
                     built-in Simple Browser, a plain link, and a ui:// resource (MCP Apps style)
    spike_block      a tool a PreToolUse hook is expected to block (see hooks/spike-hooks.json)

Run it by hand to check it starts:  py docs/spike/stub_mcp.py --self-test
Register it in the IDE with the entry printed by:  py docs/spike/checklist.py config
"""
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MCP = ROOT / "plugins" / "kirocut" / "mcp"
sys.path.insert(0, str(MCP))
import server as core  # noqa: E402

PAGE = ("<!doctype html><meta charset=utf-8><title>KiroCut spike</title>"
        "<body style='font:20px system-ui;padding:2em'><h1>SPIKE PAGE OK</h1>"
        "<p>Served from 127.0.0.1 at <span id=t></span>.</p>"
        "<p id=ck>cookie: checking...</p><p id=ls>storage: checking...</p>"
        "<script>document.getElementById('t').textContent=new Date().toLocaleTimeString();"
        "try{localStorage.setItem('k','1');document.getElementById('ls').textContent='storage: works'}catch(e){document.getElementById('ls').textContent='storage: blocked'}"
        "fetch('/cookie').then(r=>r.text()).then(x=>document.getElementById('ck').textContent='cookie: '+x);"
        "</script>")

_HTTP = []


def page_server():
    """One local page server for the spike, started on first use."""
    if _HTTP:
        return _HTTP[0]

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/cookie"):
                got = "sent" if "spike=1" in (self.headers.get("Cookie") or "") else "NOT sent (SameSite or framed)"
                body = got.encode()
                self.send_response(200)
            else:
                body = PAGE.encode()
                self.send_response(200)
                self.send_header("Set-Cookie", "spike=1; Path=/; SameSite=None; Secure")   # what KiroCut's framed pages use
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _HTTP.append(srv)
    return srv


def build():
    s = core.Server()

    @s.tool("spike_info", "Report what the IDE sent at initialize and where this server runs.", read_only=True)
    def spike_info(ctx):
        return {"client_info": s.client_info, "client_capabilities": s.client_caps, "cwd": os.getcwd(),
                "argv": sys.argv, "python": sys.version.split()[0], "platform": sys.platform,
                "env_has_workspace": {k: bool(os.environ.get(k)) for k in ("WORKSPACE_FOLDER", "KIRO_WORKSPACE", "PWD")}}

    @s.tool("spike_progress", "Run five one-second steps and report progress after each.", read_only=True)
    def spike_progress(ctx):
        for i in range(1, 6):
            time.sleep(1)
            ctx.progress(i, 5, f"step {i} of 5")
        return {"done": True, "sent_progress": ctx.token is not None}

    @s.tool("spike_elicit", "Ask the user to pick a colour through the IDE's own form.")
    def spike_elicit(ctx):
        got = ctx.elicit("Pick a colour for the spike", {
            "type": "object", "properties": {"colour": {"type": "string", "enum": ["red", "green", "blue"], "title": "Colour"}},
            "required": ["colour"]})
        return {"client_advertises_elicitation": ctx.can_elicit, "answer": got}

    @s.tool("spike_page", "Start a small local page and return links that open it three different ways.")
    def spike_page(ctx):
        port = page_server().server_address[1]
        url = f"http://127.0.0.1:{port}/"
        cmd = "command:simpleBrowser.show?" + urllib.parse.quote(json.dumps([url]), safe="")
        s.resources["ui://spike/page"] = {"name": "KiroCut spike page", "mimeType": "text/html", "text": PAGE}
        return {"url": url,
                "markdown": f"[Open in the IDE's Simple Browser]({cmd})\n\n[Open in the system browser]({url})",
                "ui_resource": "ui://spike/page",
                "note": "Tell the user to click each link and report what happened."}

    @s.tool("spike_block", "A harmless tool a PreToolUse hook should block. If it runs, the hook did not block it.")
    def spike_block(ctx):
        return {"ran": True, "meaning": "the PreToolUse hook did NOT block this call"}

    return s


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        s = build()
        assert len(s.tools) == 5, s.tools
        print("stub ok:", ", ".join(s.tools))
        sys.exit(0)
    s = build()
    s.rin, s.rout = sys.stdin.buffer, sys.stdout.buffer
    sys.stdout = sys.stderr
    s.serve()
