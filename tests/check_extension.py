#!/usr/bin/env python3
"""Checks the kirocut-view extension without an IDE: its manifest, that its JavaScript parses, that it only frames local pages,
and that the link the kirocut_open_editor tool writes is one the extension handles. Standard library and node.

    python3 tests/check_extension.py
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions" / "kirocut-view"
errors = []


def main():
    pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
    for k in ("name", "version", "publisher", "main", "engines", "activationEvents", "contributes"):
        if not pkg.get(k):
            errors.append(f"package.json: no {k}")
    if pkg.get("main") and not (EXT / pkg["main"]).is_file():
        errors.append(f"package.json: main {pkg['main']} is missing")
    cmds = {c["command"] for c in pkg.get("contributes", {}).get("commands", [])}
    if "kirocut.openEditor" not in cmds:
        errors.append("package.json: no kirocut.openEditor command")
    if "onUri" not in pkg.get("activationEvents", []):
        errors.append("package.json: it must activate on onUri to handle the chat link")
    js = (EXT / "extension.js").read_text(encoding="utf-8")
    if not re.search(r"127\\\.0\\\.0\\\.1", js):
        errors.append("extension.js: it must only frame 127.0.0.1 or localhost")
    # the link the tool writes names this extension: kiro://<publisher>.<name>/open
    tools = (ROOT / "plugins" / "kirocut" / "mcp" / "tools_editor.py").read_text(encoding="utf-8")
    want = f"kiro://{pkg['publisher']}.{pkg['name']}/open?url="
    if want not in tools:
        errors.append(f"tools_editor.py: the extension tier must write {want}")
    node = shutil.which("node")
    if node:
        r = subprocess.run([node, "--check", str(EXT / "extension.js")], capture_output=True, text=True)
        if r.returncode:
            errors.append("extension.js: " + r.stderr.strip()[:300])
        probe = (f"const m=require({json.dumps(str(EXT / 'extension.js'))});"
                 "const ok=['http://127.0.0.1:47821/?t=a','http://localhost:5000/x'].every(u=>m.localUrl(u));"
                 "const bad=['https://example.com/','http://127.0.0.1.evil.com:80/','file:///etc/passwd','http://192.168.1.2:80/','nope'].some(u=>m.localUrl(u));"
                 "if(!ok||bad){console.error('localUrl is wrong',ok,bad);process.exit(1)}")
        stub = "const Module=require('module');const o=Module._load;Module._load=function(r,...a){return r==='vscode'?{}:o.call(this,r,...a)};"
        r = subprocess.run([node, "-e", stub + probe], capture_output=True, text=True)
        if r.returncode:
            errors.append("extension.js localUrl: " + (r.stderr or r.stdout).strip()[:300])
    else:
        print("note: node not found, the JavaScript was not parsed")
    for e in errors:
        print("FAIL", e)
    print("extension ok" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
