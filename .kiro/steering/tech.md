---
inclusion: always
---

# Technology

KiroCut is a local editor. Prefer the stack already in this repo.

- **Agent surface.** Kiro reads `.kiro/steering/`, `.kiro/skills/`, and `AGENTS.md`. Each skill is a `SKILL.md` plus scripts. The real skill bodies stay in `plugins/kirocut/skills/` and `plugins/style-match/skills/`. `.kiro/skills/` is the copy Kiro loads when this folder opens, and each one points at the real file. A power install uses `plugin.json` beside those real skills. Do not invent a second editor runtime.
- **Window.** `plugins/kirocut/lib/kirocut/home.py` serves the home page (`home.html`). `review.py` serves the review page (`review.html`). Both are plain HTML, CSS and JavaScript, no framework.
- **Language.** Python 3, standard library for the window, library paths and most scripts. `python3` on macOS and Linux, `py` on Windows.
- **Picture and sound.** ffmpeg and ffprobe. Transcription is local Whisper unless the person adds an ElevenLabs key. A Gemini key is optional and only reads a reference video's look.
- **Renderer.** Remotion in `plugins/kirocut/remotion/`, run with `npx remotion`. Renders stay on the laptop unless the person picks Modal, GitHub Actions, or AWS Lambda.
- **Footage library.** `library.py` resolves it: `~/Movies/KiroCut` on macOS, `~/Videos/KiroCut` on Windows and Linux, or `KIROCUT_LIBRARY`.
- **Keys.** Saved by the setup commands into the person's own terminal, never pasted into chat. File: `~/.config/kirocut/.env`, or `$KIROCUT_HOME/.env` when that is set.

When a change can be a string, a style setting, or a taste rule, do that instead of a new dependency.
