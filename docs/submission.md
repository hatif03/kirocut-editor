# KiroCut: Kiroween 2026 submission

**Category:** Frankenstein. **Repo:** https://github.com/hatif03/KiroCut (MIT). **Pitch:** Turn your Kiro IDE into a video editor.

## What it does

You drop a talking-head take into Kiro's chat and say "edit my video". Kiro cuts out the retakes, false starts, fillers
and dead pauses, styles the cut with captions, zooms, b-roll, sound and a colour grade measured from reference videos you
choose, and renders it on your laptop. You watch it happen: the editor page opens on your raw take, ticks off each step and
strikes through every word Kiro removes as it decides. You leave notes at moments on the video, and Kiro fixes them. Small
changes are one sentence in the chat ("trim the first 2 seconds", "add a link at the end", "undo that"). Afterwards,
"show me how you edited it" plays a time-lapse of every step and change.

It also makes shorts from a long video or podcast, a launch film from a website URL, and remembers your corrections
("captions too small") for every later video.

## Why Frankenstein

KiroCut stitches together parts that were never meant to meet, and makes them one editor:

| Part | Normally | Here |
|---|---|---|
| Kiro's chat | writes code | is the editor's operator: every cut, card and render goes through it |
| An MCP server (Python stdlib) | exposes an API | is the editing surface: 22 tools that read and change a video's scene as JSON |
| A local web page | a dashboard | is the timeline, the player and the notes, inside the IDE's Simple Browser or a tab |
| Whisper (local) | transcription | finds the mistakes word by word, then checks the render heard every kept word |
| Remotion (React) | web video | renders captions, cut-aways, motion graphics and the grade on your laptop |
| A style measurer (OpenCV, OCR, audio analysis) | research tooling | turns any reference video into numbers the edit follows: cuts a minute, zooms, captions, sound, grade |
| ffmpeg-synthesised sound | nothing | the editor's own music bed and sound cues, with nothing to licence |
| Kiro hooks | lint on save | carry what you press in the editor into the chat between turns, and stop Kiro when you press Stop |

## How Kiro was used

- **Specs.** `.kiro/specs/kiro-native-editor/` (requirements in EARS form, the design with its decisions, the tasks with
  their status), plus `video-editor` and `style-match`. The spec was written first, every task names the self-check that
  proves it, and the open tasks are honest about what is not done.
- **Steering.** `.kiro/steering/`: `product`, `tech`, `structure`, `brand`, and `chat-editing`, which tells the agent to
  change a video only through the scene tools, to open the editor before cutting so the person can watch, and never to
  ask for an API key in the chat. Steering is what made the agent use the tools instead of editing JSON by hand.
- **Hooks.** `.kiro/hooks/`: a session-start check (tools missing, or the workspace not connected: it names the one
  command), a prompt hook that adds a line when something waits in the editor, a pre-tool hook that blocks every tool for
  two minutes after the person presses Stop, a stop hook, and a brand check on every save of a user-facing file (Kiro
  reviews the diff and reports a link to another creator's account or a rename of the product).
- **MCP.** The whole editor is an MCP server: scene read and change with undo, the editor window, events, questions
  (an elicitation form, or numbered chat text when the IDE has none), background renders with progress, review rounds,
  stills, replay. Without MCP the chat could only run scripts and read their text; with it the agent works on a video the
  way it works on code, with structured data and undo.
- **Custom agents.** `.kiro/agents/`: ten sub-agents, including `clip-editor` (one per short, launched in parallel),
  `cut-judge` (grades a cut against a rubric), `stills-critic`, `visual-prep` (prepares the visuals while the person reviews
  the cut) and `video-analyst` (one per reference video). They keep long transcripts out of the main session.
- **Powers.** `plugins/kirocut` and `plugins/style-match` are Kiro Powers (Agent Plugins format): one click from the
  repository URL, the MCP server starts from `${PLUGIN_ROOT}`, and the first `kirocut_status` installs the rest in the
  background.
- **Skills.** 20 skills (start, cut, style-edit, quick-edit, overlays, clips, product-video, taste, and others), each a
  `SKILL.md` with scripts, loaded from `.kiro/skills/`.
- **Kiro CLI.** The agent's decisions are tested by evals that run headless through `kiro-cli chat --v3 --no-interactive`
  with only each case's tools trusted (`tests/run_evals.py`).

## Tested against the real world

- **A real raw interview.** A NASA scientist's unedited 8 min 38 s answers (public domain): cut to 6 min 57 s, 16
  decisions on false starts, stammers and fillers, every pause tightened, 98.7% of the kept words heard in the render.
- **A real reference video.** A 15-minute colour-graded travel film, measured by the same code that then measured
  KiroCut's own render. The benchmark (`tests/bench/bench.py`) lists every number and its gap. Finding and closing those
  gaps produced real fixes: the film grade (warm highlights, teal shadows, contrast), b-roll cut-aways at the reference's
  pace, a cue that never repeats the same file, italic subtitles, long references read in minutes instead of hours, and a
  render roughly seven times faster with clip proxies.
- **Examples.** `docs/examples/` and the editor's Home: previews of what it made, only from footage anyone may publish.

## Try it (judges)

1. Install Kiro, Node 20+, Python 3.10+ and ffmpeg (the README lists one command per OS).
2. In Kiro: Powers, Add Custom Power, Import power from a repository URL:
   `https://github.com/hatif03/KiroCut/tree/main/plugins/kirocut`. Or clone the repo, open it, and run
   `node plugins/kirocut/mcp/launch.mjs --run plugins/kirocut/skills/setup/scripts/setup.py workspace` once.
3. Say **edit my video** and drop a clip of yourself talking. The first run installs the rest (5-10 minutes, once).

## Demo video (under 3 minutes)

| Time | Shot |
|---|---|
| 0:00-0:12 | The mark, then the pitch on screen: "Turn your Kiro IDE into a video editor." |
| 0:12-0:35 | Kiro IDE: drop the raw NASA interview into the chat, say "edit my video". The editor opens beside the chat on the raw take. |
| 0:35-1:05 | The live cut: steps tick off, the transcript strikes the fillers and stammers as Kiro decides. |
| 1:05-1:35 | The styled edit: b-roll cut-aways, the grade, captions; a note left at a moment; Kiro fixes it. |
| 1:35-1:55 | "Trim the first 2 seconds", "undo that", in the chat, with the page redrawing. |
| 1:55-2:20 | The replay time-lapse of the whole edit. |
| 2:20-2:45 | The benchmark report: the reference and KiroCut's render measured the same way, first draft against the improved one. |
| 2:45-2:58 | Install in one click from the Powers panel. The repo URL. |

Footage: the NASA interview and b-roll (public domain), the editor's own synthesised music. No third-party music, and the
reference video is not shown.
