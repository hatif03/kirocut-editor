# Kiro IDE compatibility

What KiroCut relies on in the Kiro IDE, what the docs confirm, and what only a run in the IDE can confirm.
The spike in `docs/spike/` answers the open rows. Until a row is recorded, KiroCut uses the **default** in the last column,
which works either way.

Docs read: [MCP](https://kiro.dev/docs/mcp/), [MCP configuration](https://kiro.dev/docs/mcp/configuration/),
[Hooks](https://kiro.dev/docs/hooks/) and [triggers](https://kiro.dev/docs/hooks/types/),
[Powers](https://kiro.dev/docs/powers/create/), [Skills](https://kiro.dev/docs/skills/),
[Custom agents](https://kiro.dev/docs/custom-agents/) and [sub-agents](https://kiro.dev/docs/custom-agents/subagents/).
Checked 24 Nov 2026.

## Matrix

| # | Question | From the docs | Spike key | Default until recorded |
|---|---|---|---|---|
| 1 | A Power's `mcp.json` loads and its tools are callable | Yes. Server is namespaced `power-<power>-<server>`. | `mcp_loads` | assume yes |
| 2 | Tool id length | Name plus prefix within 64 characters; `^[a-zA-Z][a-zA-Z0-9_]*$`; non-empty description | none (tested in `test_server.py`) | tool names 38 characters or fewer |
| 3 | A relative path in `mcp.json` resolves from the workspace (or the Power) folder | Not documented | `mcp_cwd_root` | `launch.mjs` found by relative path; if no, use an absolute path written by setup |
| 4 | Progress notifications show in the chat | Not documented | `progress_shows` | send them, and also keep `kirocut_job` pollable |
| 5 | Elicitation renders a form | The MCP page lists "respond to server elicitation requests"; per-surface support not listed | `elicit_renders` | ask through the client when it advertises `elicitation`, else numbered chat text |
| 6 | `PromptSubmit` command hook stdout reaches the agent | Yes: exit 0 adds stdout to context | `hook_prompt` | inject pending window events |
| 7 | `PreToolUse` can block one MCP server's tools | Yes: matcher `@<server>`; non-zero exit blocks | `hook_block` | window Stop denies calls until cleared |
| 8 | `Stop` fires after each turn | Yes | `hook_stop` | clear the busy flag |
| 9 | A `command:` link in chat markdown runs `simpleBrowser.show` | Not documented | `command_link`, `simple_frame` | system browser |
| 10 | An extension webview can frame `http://127.0.0.1:<port>` | Not documented; standard in VS Code-style IDEs | `extension_panel` | system browser |
| 11 | A tool result `ui://` resource renders inline (MCP Apps) | Not documented | `ui_resource` | not used |
| 12 | Hooks have no `Notification` event | Confirmed absent | none | the window shows "needs you in the chat" itself |
| 13 | Nothing outside the IDE can push a prompt into the chat | No such API documented | none | three routes together: `kirocut_events` long poll, `PromptSubmit` injection, a "Tell Kiro to continue" button |
| 14 | Custom agents run as parallel sub-agents | Yes: `.kiro/agents/*.md`, own context, shared MCP servers | none | sequential fallback in each skill |
| 15 | Workspace settings in `.kiro/settings/` | Kiro keeps this folder write-protected for agents | none | the user adds `.kiro/settings/mcp.json` (content in `docs/spike/workspace-mcp.json`) |

## Decision rules

`py docs/spike/checklist.py decide` writes `plugins/kirocut/mcp/compat.json`. The server reads it.

- **Embed tier.** `extension_panel=yes` gives `extension`. Else `command_link=yes` and `simple_frame=yes` gives `simple-browser`. Else `browser`.
  Every tier returns the URL in the tool result.
- **Questions.** `elicit_renders=no` gives `chat` (always numbered text). Otherwise `auto`: elicit when the client advertises it.
- **Window events.** `hook_prompt=no` gives `tool-only`: no hook injection, the agent must hold `kirocut_events`.

## How to run the spike

`py docs/spike/checklist.py` prints the steps (about 20 minutes in the IDE). Record with
`py docs/spike/checklist.py record key=yes|no ...`, then `py docs/spike/checklist.py decide`.

## Results

Not recorded yet. The defaults above are in force. Record results here after running the checklist:

| Date | IDE version | Answers recorded |
|---|---|---|
| | | |
