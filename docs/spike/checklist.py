#!/usr/bin/env python3
"""The spike checklist for the Kiro IDE, and the step that turns its answers into KiroCut's defaults.

    py docs/spike/checklist.py              print the steps to try in the IDE
    py docs/spike/checklist.py config       print the MCP config entry for the stub server
    py docs/spike/checklist.py record k=v ...   save answers (keys below) to docs/spike/results.json
    py docs/spike/checklist.py decide       write plugins/kirocut/mcp/compat.json from the answers
    py docs/spike/checklist.py demo         self-check

Answer keys (yes / no):
    mcp_loads         the stub server's tools show in the MCP Servers tab and the chat can call spike_info
    mcp_cwd_root      spike_info's cwd is the workspace folder (so a relative path in mcp.json works)
    progress_shows    spike_progress showed live progress in the chat
    elicit_renders    spike_elicit showed a form in the IDE and the answer came back
    hook_prompt       the agent repeated the SPIKE-HOOK-OK marker (PromptSubmit stdout reaches it)
    hook_block        spike_block was blocked and the agent saw SPIKE-BLOCKED (PreToolUse exit 2)
    hook_stop         docs/spike/hooks/stop.log gained a line after a turn
    command_link      the "Simple Browser" link in the chat opened the IDE's built-in browser panel
    simple_frame      that panel showed SPIKE PAGE OK (and say whether 'cookie' read sent: cookie_sent=yes/no)
    extension_panel   the probe extension's panel framed the page
    ui_resource       the IDE rendered the ui:// resource inline
    uri_handler       the extension's URI link opened a panel
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results.json"
COMPAT = ROOT / "plugins" / "kirocut" / "mcp" / "compat.json"
KEYS = ("mcp_loads", "mcp_cwd_root", "progress_shows", "elicit_renders", "hook_prompt", "hook_block", "hook_stop",
        "command_link", "simple_frame", "cookie_sent", "extension_panel", "ui_resource", "uri_handler")

STEPS = f"""KiroCut compatibility spike: run these in the Kiro IDE, then record the answers.

A. The MCP server (about 5 minutes)
  1. Add the stub server: run `py docs/spike/checklist.py config`, paste the entry into the workspace MCP config
     (command palette: "Kiro: Open workspace MCP config (JSON)"), save. Open the MCP Servers tab: "spike" should connect.
  2. In a chat in this workspace say: "call spike_info and show me everything it returns".
       -> record mcp_loads, mcp_cwd_root (is cwd {ROOT}?)
  3. Say: "call spike_progress". Watch the chat while it runs.
       -> record progress_shows
  4. Say: "call spike_elicit". A form should appear in the IDE.
       -> record elicit_renders (if no form: the tool returns answer null and you can answer in chat)

B. Hooks (about 5 minutes)
  5. Copy docs/spike/hooks/spike-hooks.json to .kiro/hooks/spike-hooks.json.
  6. Send any message. Ask: "what SPIKE-HOOK-OK marker did you see?"        -> record hook_prompt
  7. Say: "call spike_block".                                               -> record hook_block
  8. After a turn, look for docs/spike/hooks/stop.log.                      -> record hook_stop
  9. Delete .kiro/hooks/spike-hooks.json when done.

C. Showing the page in the IDE (about 10 minutes)
 10. Say: "call spike_page and show me its markdown links exactly as written".
 11. Click "Open in the IDE's Simple Browser".   -> record command_link, simple_frame (page says SPIKE PAGE OK?),
     cookie_sent (what does the 'cookie:' line say? sent = yes)
 12. Probe extension (optional): in docs/spike/probe-ext run `npx @vscode/vsce package --allow-missing-repository`,
     then in the IDE: Extensions, "..." menu, Install from VSIX. Run "KiroCut probe: open a local page in a panel"
     and paste the URL from step 10.             -> record extension_panel
 13. If the chat showed the ui:// resource inline, record ui_resource=yes. Otherwise no.

Record, for example:
  py docs/spike/checklist.py record mcp_loads=yes mcp_cwd_root=yes progress_shows=no elicit_renders=yes hook_prompt=yes
  py docs/spike/checklist.py decide
"""


def load():
    try:
        return json.loads(RESULTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def decide(r):
    """KiroCut's defaults from the answers. Anything not answered keeps the safe default."""
    yes = lambda k: str(r.get(k, "")).lower() in ("yes", "y", "true", "1")
    answered = lambda k: k in r
    if yes("extension_panel"):
        embed = "extension"
    elif yes("command_link") and yes("simple_frame"):
        embed = "simple-browser"
    else:
        embed = "browser"
    return {
        "embed": embed,
        # "auto": ask through the client when it advertises elicitation; "chat": always ask in chat text
        "elicitation": "chat" if answered("elicit_renders") and not yes("elicit_renders") else "auto",
        "progress": "notify" if yes("progress_shows") or not answered("progress_shows") else "poll",
        # whether the window's events reach the agent through the PromptSubmit hook, or only through kirocut_events
        "prompt_hook": "inject" if yes("hook_prompt") or not answered("hook_prompt") else "tool-only",
        "framed_cookie": "yes" if yes("cookie_sent") else "no",   # informational: the page always also accepts the header
        "mcp_relative_path": "yes" if yes("mcp_cwd_root") else ("no" if answered("mcp_cwd_root") else "unknown"),
        "recorded": sorted(r),
    }


def demo():
    d = decide({})
    assert d["embed"] == "browser" and d["elicitation"] == "auto" and d["prompt_hook"] == "inject", d
    d = decide({"command_link": "yes", "simple_frame": "yes"})
    assert d["embed"] == "simple-browser", d
    d = decide({"command_link": "yes", "simple_frame": "no", "extension_panel": "no"})
    assert d["embed"] == "browser", d
    assert decide({"extension_panel": "yes", "command_link": "yes", "simple_frame": "yes"})["embed"] == "extension"
    assert decide({"elicit_renders": "no"})["elicitation"] == "chat"
    assert decide({"hook_prompt": "no"})["prompt_hook"] == "tool-only"
    assert decide({"mcp_cwd_root": "no"})["mcp_relative_path"] == "no"
    print("checklist demo ok")
    return 0


def main(a):
    cmd = a[0] if a else ""
    if cmd == "demo":
        return demo()
    if cmd == "config":
        stub = (HERE / "stub_mcp.py").as_posix()
        print(json.dumps({"mcpServers": {"spike": {"command": "py" if sys.platform == "win32" else "python3", "args": [stub]}}}, indent=2))
        return 0
    if cmd == "record":
        r = load()
        for kv in a[1:]:
            k, _, v = kv.partition("=")
            if k not in KEYS or v not in ("yes", "no"):
                sys.exit(f"record takes key=yes|no with a key from: {', '.join(KEYS)}")
            r[k] = v
        RESULTS.write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(f"saved {len(r)} answers to {RESULTS}")
        return 0
    if cmd == "decide":
        d = decide(load())
        COMPAT.parent.mkdir(parents=True, exist_ok=True)
        COMPAT.write_text(json.dumps(d, indent=1), encoding="utf-8")
        print(json.dumps(d, indent=1))
        return 0
    print(STEPS)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
