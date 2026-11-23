#!/usr/bin/env python3
"""KiroCut's MCP server: typed tools for the Kiro chat. Python standard library only.

    python3 server.py              speak MCP over stdio (what mcp.json starts)
    python3 server.py --list       print the tools as JSON and exit
    python3 server.py demo         self-check (a child server, JSON-RPC over pipes)

The transport is MCP's stdio one: one JSON message per line on stdin and stdout. stdout carries
protocol only. Anything a tool (or a module it imports) prints goes to stderr, because `sys.stdout`
is pointed at stderr before a tool runs.

Each request runs on its own thread, so a long poll (`kirocut_events`) never blocks another call,
a cancel or a ping. A tool receives a `Ctx`: `progress()` sends a progress notification when the
caller asked for one, `elicit()` asks the user a question through the client when it supports
elicitation (and returns None when it does not), `cancelled` is set when the client cancels.

A failure a tool names is a `ToolError(code, message, hint)`. The client sees the tool result with
`isError` true and `{"code", "message", "hint"}` as its text. Anything else a tool raises is
reported as code `internal` with the exception text, never a stack trace on stdout.
"""
import json
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
LIB = PLUGIN / "lib"
for _p in (str(LIB), str(LIB / "kirocut")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SERVER_NAME = "kirocut"
VERSION = "1.0.0"
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")   # newest first
NAME_OK = __import__("re").compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
NAME_MAX = 38   # Kiro names a Power's tool mcp_power-kirocut-kirocut_<tool> (26 characters before the tool); the whole id must stay within 64


class ToolError(Exception):
    """A failure the agent can act on: a stable code, one sentence, and what to do next."""

    def __init__(self, code, message, hint=""):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint

    def body(self):
        return {"code": self.code, "message": self.message, "hint": self.hint}


class Tool:
    def __init__(self, name, description, schema, fn, read_only=False):
        if not NAME_OK.match(name) or len(name) > NAME_MAX:
            raise ValueError(f"bad tool name {name!r}")
        if not description.strip():
            raise ValueError(f"tool {name} has no description")
        self.name, self.description, self.fn, self.read_only = name, description, fn, read_only
        self.schema = schema or {"type": "object", "properties": {}}

    def listing(self):
        return {"name": self.name, "description": self.description, "inputSchema": self.schema,
                "annotations": {"readOnlyHint": self.read_only}}


class Ctx:
    """What a running tool gets from its request."""

    def __init__(self, server, token):
        self.server, self.token, self.cancelled = server, token, threading.Event()

    def progress(self, done, total=None, message=None):
        if self.token is None:
            return
        p = {"progressToken": self.token, "progress": done}
        if total is not None:
            p["total"] = total
        if message:
            p["message"] = message
        self.server.notify("notifications/progress", p)

    @property
    def can_elicit(self):
        return "elicitation" in (self.server.client_caps or {})

    def elicit(self, message, schema, timeout=600):
        """Ask the user through the client. {"action": accept|decline|cancel, "content": {...}}, or None
        when the client has no elicitation (the caller then asks in the chat)."""
        if not self.can_elicit:
            return None
        return self.server.request("elicitation/create", {"message": message, "requestedSchema": schema}, timeout, self)


class Server:
    def __init__(self, stdin=None, stdout=None):
        self.tools = {}
        self.resources = {}   # uri -> {"name", "mimeType", "text"}
        self.client_caps, self.client_info = {}, {}
        self.rin = stdin or sys.stdin.buffer
        self.rout = stdout or sys.stdout.buffer
        self.wlock = threading.Lock()
        self.pending = {}     # id -> queue for a server-to-client request
        self.running = {}     # request id -> Ctx
        self.next_id = 1
        self.done = threading.Event()

    # ---- registry
    def tool(self, name, description, schema=None, read_only=False):
        def deco(fn):
            self.tools[name] = Tool(name, description, schema, fn, read_only)
            return fn
        return deco

    # ---- wire
    def send(self, msg):
        line = (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")
        with self.wlock:
            try:
                self.rout.write(line)
                self.rout.flush()
            except (OSError, ValueError):
                self.done.set()

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method, params, timeout=600, ctx=None):
        with self.wlock:
            rid = f"s{self.next_id}"
            self.next_id += 1
        q = self.pending[rid] = queue.Queue()
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        end = time.time() + timeout
        try:
            while time.time() < end and not self.done.is_set():
                if ctx is not None and ctx.cancelled.is_set():
                    return {"action": "cancel"}
                try:
                    r = q.get(timeout=0.25)
                except queue.Empty:
                    continue
                if "error" in r:
                    raise ToolError("client_error", str(r["error"].get("message", "the client refused")), "")
                return r.get("result")
            return {"action": "cancel"}
        finally:
            self.pending.pop(rid, None)

    # ---- handlers
    def handle(self, msg):
        method, rid = msg.get("method"), msg.get("id")
        if method is None:   # a response to one of our requests
            q = self.pending.get(rid)
            if q:
                q.put(msg)
            return
        params = msg.get("params") or {}
        if rid is None:      # a notification
            if method == "notifications/cancelled":
                c = self.running.get(params.get("requestId"))
                if c:
                    c.cancelled.set()
            return
        try:
            result = self.dispatch(method, params, rid)
        except ToolError as e:
            return self.send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": e.message, "data": e.body()}})
        except KeyError as e:
            return self.send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"unknown {e.args[0]}"}})
        except Exception as e:   # noqa: BLE001  never a stack trace on the wire
            traceback.print_exc(file=sys.stderr)
            return self.send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}})
        self.send({"jsonrpc": "2.0", "id": rid, "result": result})

    def dispatch(self, method, params, rid):
        if method == "initialize":
            self.client_caps = params.get("capabilities") or {}
            self.client_info = params.get("clientInfo") or {}
            want = params.get("protocolVersion")
            return {"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                    "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": VERSION},
                    "instructions": "KiroCut edits videos. Start with kirocut_status. Read state with the *_show tools, change a scene "
                                    "with kirocut_scene_ops, and use kirocut_events to hear what the user did in the editor window."}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [t.listing() for t in self.tools.values()]}
        if method == "tools/call":
            return self.call(params, rid)
        if method == "resources/list":
            return {"resources": [{"uri": u, "name": r["name"], "mimeType": r["mimeType"]} for u, r in self.resources.items()]}
        if method == "resources/read":
            r = self.resources[params.get("uri")]
            return {"contents": [{"uri": params["uri"], "mimeType": r["mimeType"], "text": r["text"]}]}
        raise KeyError(method)

    def call(self, params, rid):
        t = self.tools.get(params.get("name"))
        if not t:
            raise ToolError("unknown_tool", f"no tool named {params.get('name')}", "call tools/list for the names")
        token = (params.get("_meta") or {}).get("progressToken")
        ctx = Ctx(self, token)
        self.running[rid] = ctx
        try:
            out = t.fn(ctx, **(params.get("arguments") or {}))
            return {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)}], "isError": False}
        except ToolError as e:
            return {"content": [{"type": "text", "text": json.dumps(e.body(), ensure_ascii=False)}], "isError": True}
        except TypeError as e:
            if "argument" in str(e):
                return {"content": [{"type": "text", "text": json.dumps(
                    {"code": "bad_arguments", "message": str(e), "hint": f"see inputSchema of {t.name}"})}], "isError": True}
            raise
        except Exception as e:   # noqa: BLE001
            traceback.print_exc(file=sys.stderr)
            return {"content": [{"type": "text", "text": json.dumps(
                {"code": "internal", "message": f"{type(e).__name__}: {e}", "hint": "see the server log (stderr)"})}], "isError": True}
        finally:
            self.running.pop(rid, None)

    # ---- loop
    def serve(self):
        for line in iter(self.rin.readline, b""):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line.decode("utf-8"))
            except ValueError:
                self.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
                continue
            if msg.get("method") is None or msg.get("id") is None and msg.get("method") == "notifications/cancelled":
                self.handle(msg)   # responses and cancels are instant
            else:
                threading.Thread(target=self.handle, args=(msg,), daemon=True).start()
        self.done.set()


def build():
    """The server with every KiroCut tool registered."""
    s = Server()
    import tools
    tools.register(s)
    return s


def main(argv):
    if argv[:1] == ["demo"]:
        sys.path.insert(0, str(HERE))
        import test_server
        return test_server.demo()
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    s = build()
    if argv[:1] == ["--list"]:
        print(json.dumps([t.listing() for t in s.tools.values()], indent=1))
        return 0
    if os.name == "nt":   # a Windows pipe must not turn \n into \r\n
        import msvcrt
        for f in (sys.stdin, sys.stdout):
            msvcrt.setmode(f.fileno(), os.O_BINARY)
    # The protocol keeps private copies of fds 0 and 1. A child process a tool starts (setup's checks, ffmpeg, npx)
    # inherits fds 0 and 1, so 0 becomes an empty input (npx asking "Ok to proceed?" would wait on the protocol
    # pipe forever) and 1 becomes stderr (a child's print must never land in the protocol).
    sys.stdout.flush()
    fin, fout = os.dup(0), os.dup(1)   # not inheritable (os.dup's default): no child holds the protocol open
    if os.name == "nt":
        for fd in (fin, fout):
            msvcrt.setmode(fd, os.O_BINARY)
    s.rin, s.rout = os.fdopen(fin, "rb"), os.fdopen(fout, "wb")
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)
    os.dup2(2, 1)
    sys.stdout = sys.stderr   # a module a tool imports may print: that must never land in the protocol
    s.serve()
    return 0


if __name__ == "__main__":
    import server as _self   # the tools import `server`: run that one module, not a second copy named __main__
    sys.exit(_self.main(sys.argv[1:]))
