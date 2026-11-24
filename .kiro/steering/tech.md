---
inclusion: always
---

# Technology

KiroCut is a local editor. Prefer the stack already in this repo.

- **Agent surface.** Kiro reads `.kiro/steering/`, `.kiro/skills/`, and `AGENTS.md`. Each skill is a `SKILL.md` plus scripts. The real skill bodies stay in `plugins/kirocut/skills/` and `plugins/style-match/skills/`. `.kiro/skills/` is the copy Kiro loads when this folder opens, and each one points at the real file. A power install uses `plugin.json` beside those real skills. Do not invent a second editor runtime.
- **Chat tools.** The chat drives the editor through the `kirocut` MCP server in `plugins/kirocut/mcp/` (`server.py`, Python standard library only, started by `launch.mjs` so one `mcp.json` works on Windows and Mac). Tools return JSON and fail with `{code, message, hint}`; they call `scene.py`, `review.py`, `home.py` and `taste.py` in-process. Questions go through `kirocut_ask` (a form when the IDE supports elicitation, else numbered chat text). What the user does in the window reaches the chat through `kirocut_events` and the hooks in `.kiro/hooks/` (`lib/kirocut/kirohook.py`). Tool names stay at 38 characters or fewer.
- **Kiro files.** `.kiro/skills/` and `.kiro/agents/` are generated from `plugins/` by `python3 tests/sync_kiro.py`; `check_plugins.py` fails when they drift. Edit the plugin copy, then sync. `.kiro/settings/mcp.json` is the user's: content in `docs/spike/workspace-mcp.json`. What the IDE supports is in `docs/KIRO-COMPAT.md`; `plugins/kirocut/mcp/compat.json` holds the decisions.
- **Window.** `plugins/kirocut/lib/kirocut/home.py` serves the home page (`home.html`). `review.py` serves the review page (`review.html`). Both are plain HTML, CSS and JavaScript, no framework.
- **Language.** Python 3, standard library for the window, library paths and most scripts. `python3` on macOS and Linux, `py` on Windows.
- **Picture and sound.** ffmpeg and ffprobe. Transcription is local Whisper unless the person adds an ElevenLabs key. A Gemini key is optional and only reads a reference video's look.
- **Renderer.** Remotion in `plugins/kirocut/remotion/`, run with `npx remotion`. Renders stay on the laptop unless the person picks Modal, GitHub Actions, or AWS Lambda.
- **Footage library.** `library.py` resolves it: `~/Movies/KiroCut` on macOS, `~/Videos/KiroCut` on Windows and Linux, or `KIROCUT_LIBRARY`.
- **Keys.** Saved by the setup commands into the person's own terminal, never pasted into chat. File: `~/.config/kirocut/.env`, or `$KIROCUT_HOME/.env` when that is set.

When a change can be a string, a style setting, or a taste rule, do that instead of a new dependency.
