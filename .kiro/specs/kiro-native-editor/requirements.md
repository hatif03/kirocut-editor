# Requirements: KiroCut, a Kiro-native video editor driven from the chat

## Introduction

KiroCut turns the Kiro IDE into a video editor. The person drops a talking-head take into Kiro's chat (or the editor
window), and Kiro cuts it, styles it and renders it, while the person watches and leaves notes. This spec covers what
makes it Kiro-native: the chat drives every step through an MCP server, the person sees the edit happen, it installs in
one step, and it holds up against real footage and a real reference video.

## Requirement 1: The chat drives the editor

**User story:** As a person editing in Kiro, I want to say "edit my video" and small changes in the chat, so that I never
leave the IDE to drive a separate editor.

1. WHEN the workspace opens THEN Kiro SHALL start the `kirocut` MCP server (Python standard library, started by
   `launch.mjs` so one config works on Windows and macOS).
2. WHEN the agent reads or changes a video THEN it SHALL do so through tools that return JSON (`kirocut_scene_show`,
   `kirocut_scene_ops`, `kirocut_scene_add`, `kirocut_scene_undo`), never by editing files by hand.
3. WHEN a tool fails THEN it SHALL return `{code, message, hint}` and the server SHALL keep running.
4. WHEN the person presses something in the editor window THEN `kirocut_events` SHALL deliver it to the chat exactly once,
   and a hook SHALL add a line between turns when something is waiting.
5. WHEN the agent asks a question THEN it SHALL use `kirocut_ask`: a form when the IDE supports MCP elicitation, else
   numbered choices in the chat.
6. WHEN the person says "undo that" THEN the agent's newest scene change SHALL be undone with no change number needed.
7. WHEN a tool starts a child process THEN the child SHALL NOT be able to read from or write to the MCP connection.

## Requirement 2: The person watches Kiro edit

1. WHEN a new edit starts from the chat THEN the editor page SHALL open on the raw take before the cut exists
   (`kirocut_open_editor` with `source`).
2. WHILE the cut is made THEN the page SHALL tick off each step the cut scripts report, with no home-window job needed.
3. WHILE Kiro decides the cut THEN the page SHALL show the transcript with each removed word struck through.
4. WHEN Kiro changes the scene through the page THEN the player and timeline SHALL redraw.
5. WHEN the person asks how it was made THEN `kirocut_replay` SHALL produce a labelled time-lapse of every step, change and
   draft, playable on the review page.

## Requirement 3: One-step install

1. WHEN the person installs the Kiro Power from its repository folder URL THEN the `kirocut` tools SHALL start from the
   power's own folder (`${PLUGIN_ROOT}` in `mcp.json`).
2. WHEN `kirocut_status` first runs on a machine missing what KiroCut can install itself (Python packages, the speech
   model, the renderer) THEN it SHALL start installing them as one background job, once.
3. IF a system tool (Python, ffmpeg, Node, git) is missing THEN it SHALL return the exact command for the person's own
   terminal and SHALL NOT install past it.
4. WHEN the repo is cloned and the tools are not connected THEN the session hook SHALL give the one command that writes
   `.kiro/settings/mcp.json`.

## Requirement 4: Real footage, measured against a real reference

1. WHEN a reference video is given THEN style-match SHALL measure it (pace, zooms, captions, graphics, sound, grade) into
   a `style.json`, within minutes even for a long video.
2. WHEN KiroCut's edit is compared with the reference THEN both SHALL be measured by the same code, and the report SHALL
   list every number with its gap and whether it is within 25%.
3. WHEN the reference has a film grade THEN the edit SHALL match its warmth, shadow tint and contrast within limits.
4. WHEN a creator cuts away from themselves THEN the edit SHALL show the person's b-roll full frame on the lines it fits.
5. WHEN a cue repeats THEN it SHALL play a different take, never the same file twice running.
6. WHEN a card plays a clip THEN the render SHALL read a proxy of it, so a long edit renders in reasonable time.

## Requirement 5: Examples anyone can watch

1. WHEN an edit is kept as an example THEN it SHALL be saved only if anyone may publish its footage (public domain, CC0,
   CC BY, or the person's own), and SHALL refuse another creator's video or a social account's link.
2. WHEN the editor's Home opens THEN it SHALL list the examples with a poster, a preview, the replay and the raw take.
