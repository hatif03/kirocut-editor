#!/usr/bin/env python3
"""Self-check for the MCP server: a real child process spoken to over pipes, and an in-process server
for the parts a child can't show (progress, elicitation, cancel). No network, no keys.

    python3 test_server.py            same as `server.py demo`

`Client` is also what the other tool tests use: `with Client() as c: c.call("kirocut_status", doctor=False)`.
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import server as srv  # noqa: E402

LIMIT = 64
PREFIX = "mcp_power-kirocut-kirocut_"   # how Kiro names a Power's server in hook events; the real tool id adds the tool name


class Client:
    """A child `server.py` and a JSON-RPC conversation with it."""

    def __init__(self, env=None, caps=None):
        e = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
        self.p = subprocess.Popen([sys.executable, str(HERE / "server.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=e)
        self.n = 0
        self.caps = caps or {}
        self.notes = []
        self.answer = None   # fn(request) -> result: how this fake IDE answers an elicitation

    def __enter__(self):
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": self.caps, "clientInfo": {"name": "test", "version": "0"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def __exit__(self, *a):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()

    def send(self, msg):
        self.p.stdin.write((json.dumps(msg) + "\n").encode())
        self.p.stdin.flush()

    def rpc(self, method, params=None, timeout=60):
        self.n += 1
        self.send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}})
        end = time.time() + timeout
        while time.time() < end:
            line = self.p.stdout.readline()
            if not line:
                raise AssertionError("server closed: " + self.p.stderr.read().decode(errors="replace")[-800:])
            m = json.loads(line)   # a line that is not JSON would be a protocol leak: fail loudly
            if m.get("id") == self.n and "method" not in m:
                return m
            if "method" in m and m.get("id") is not None and self.answer:   # the server asks the client something
                self.send({"jsonrpc": "2.0", "id": m["id"], "result": self.answer(m)})
                continue
            self.notes.append(m)
        raise AssertionError(f"no answer to {method}")

    def call(self, name, **args):
        """(is_error, parsed JSON of the tool's text)."""
        r = self.rpc("tools/call", {"name": name, "arguments": args})["result"]
        return r["isError"], json.loads(r["content"][0]["text"])


def pipes():
    """A Server wired to two OS pipes, and the test's ends of them."""
    a_r, a_w = os.pipe()   # test -> server
    b_r, b_w = os.pipe()   # server -> test
    s = srv.Server(os.fdopen(a_r, "rb"), os.fdopen(b_w, "wb"))
    t = threading.Thread(target=s.serve, daemon=True)
    t.start()
    return s, os.fdopen(a_w, "wb"), os.fdopen(b_r, "rb")


def put(w, msg):
    w.write((json.dumps(msg) + "\n").encode())
    w.flush()


def get(r):
    return json.loads(r.readline())


def demo():
    # 1. the real server in a child process
    with Client() as c:
        init = c.rpc("initialize", {"protocolVersion": "2099-01-01", "capabilities": {}})["result"]
        assert init["protocolVersion"] == srv.PROTOCOLS[0] and init["serverInfo"]["name"] == "kirocut", init
        tools = c.rpc("tools/list")["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "kirocut_status" in names, names
        for t in tools:   # Kiro drops a tool whose name or description fails these
            assert srv.NAME_OK.match(t["name"]) and len(PREFIX + t["name"]) <= LIMIT, t["name"]
            assert t["description"].strip() and t["inputSchema"]["type"] == "object", t["name"]
        assert len(set(names)) == len(names), "duplicate tool"
        err, st = c.call("kirocut_status", doctor=False)
        assert not err and st["library"] and st["platform"], st
        # the doctor starts child processes (node, npx, the venv): they get an empty stdin, not the protocol pipe,
        # or one waiting on input (npx's "Ok to proceed?") hangs the session (found on the Windows sample run)
        err, st = c.call("kirocut_status")
        assert not err and isinstance(st["tools"], list) and st["tools"], st
        err, bad = c.call("kirocut_status", nonsense=1)
        assert err and bad["code"] == "bad_arguments", bad
        r = c.rpc("tools/call", {"name": "no_such_tool", "arguments": {}})
        assert "error" in r and r["error"]["data"]["code"] == "unknown_tool", r
        assert c.rpc("ping")["result"] == {}
        assert "error" in c.rpc("nope/nothing")
        print(f"mcp      ok: {len(names)} tools, names and schemas valid, errors coded, stdout is protocol only")

    # 2. progress, elicitation, cancel, stdout hygiene, in process
    s, w, r = pipes()

    @s.tool("t_progress", "Report progress.", read_only=True)
    def t_progress(ctx):
        for i in range(1, 4):
            ctx.progress(i, 3, f"step {i}")
        return {"ok": True}

    @s.tool("t_ask", "Ask the user.")
    def t_ask(ctx):
        got = ctx.elicit("Which?", {"type": "object", "properties": {"pick": {"type": "string"}}})
        return {"asked": got is not None, "got": got}

    @s.tool("t_print", "A tool that prints.")
    def t_print(ctx):
        real, sys.stdout = sys.stdout, sys.stderr
        try:
            print("this must not reach the protocol")
        finally:
            sys.stdout = real
        return {"ok": True}

    @s.tool("t_wait", "Wait until cancelled.")
    def t_wait(ctx):
        return {"cancelled": ctx.cancelled.wait(10)}

    put(w, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}}}})
    assert get(r)["result"]["capabilities"]["tools"] == {"listChanged": False}
    put(w, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "t_progress", "arguments": {}, "_meta": {"progressToken": "tk"}}})
    seen = []
    while True:
        m = get(r)
        if m.get("id") == 2:
            break
        seen.append(m)
    assert [x["params"]["progress"] for x in seen if x["method"] == "notifications/progress"] == [1, 2, 3], seen
    assert all(x["params"]["progressToken"] == "tk" for x in seen)
    put(w, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "t_progress", "arguments": {}}})
    assert get(r)["id"] == 3, "no progress notifications without a token"
    put(w, {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "t_ask", "arguments": {}}})
    q = get(r)
    assert q["method"] == "elicitation/create" and q["params"]["message"] == "Which?", q
    put(w, {"jsonrpc": "2.0", "id": q["id"], "result": {"action": "accept", "content": {"pick": "b"}}})
    got = json.loads(get(r)["result"]["content"][0]["text"])
    assert got == {"asked": True, "got": {"action": "accept", "content": {"pick": "b"}}}, got
    put(w, {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "t_wait", "arguments": {}}})
    time.sleep(0.2)
    put(w, {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 5}})
    assert json.loads(get(r)["result"]["content"][0]["text"]) == {"cancelled": True}, "a cancel reaches the running tool"
    put(w, {"jsonrpc": "2.0", "id": 6, "method": "ping"})
    assert get(r)["id"] == 6
    w.close()
    # no elicitation capability: the tool is told so and asks in chat instead
    s2, w2, r2 = pipes()
    s2.tools["t_ask"] = s.tools["t_ask"]
    put(w2, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
    get(r2)
    put(w2, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "t_ask", "arguments": {}}})
    assert json.loads(get(r2)["result"]["content"][0]["text"]) == {"asked": False, "got": None}
    w2.close()
    print("mcp      ok: progress, elicitation (and its absence), cancel, concurrent requests")
    import test_tools
    test_tools.demo()
    print("mcp server demo ok")
    return 0


if __name__ == "__main__":
    sys.exit(demo())
