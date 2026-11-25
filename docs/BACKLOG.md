# Backlog

Ranked by value to a first-time user. One item at a time; each lands with a test that fails before
and passes after. Done items move to CHANGELOG.md.

Sources: a first-time user's path through setup, a cut, and a styled edit.

## Now

(empty: the next item comes from Next)

## Next

Kiro IDE (the chat-driven editor, see docs/KIRO-COMPAT.md):
- Run the IDE spike (`py docs/spike/checklist.py`, about 20 minutes) and record the answers. Until then the editor opens in the
  browser and questions use elicitation only if the client advertises it. A recorded `extension_panel=yes` or
  `command_link=yes` + `simple_frame=yes` switches `kirocut_open_editor` to the IDE panel (`checklist.py decide`).
- Add `.kiro/settings/mcp.json` (Kiro keeps that folder to itself: copy `docs/spike/workspace-mcp.json`). Check the
  relative path to `launch.mjs` resolves from the workspace folder (spike key `mcp_cwd_root`); if not, write an absolute path.
- The sample take in a real Kiro IDE chat, on a clean Windows and Mac machine. The same steps ran on Windows through the
  MCP server as the chat calls it (a synthetic spoken take: status, transcribe, cut, review round, scene edits, stills,
  render); the IDE's own pieces (hooks between turns, elicitation forms) still need the spike.
- Run the evals once with the Kiro CLI (`python3 tests/run_evals.py --runs 1`) and fix the tool names in each case's `tools`
  if the CLI names its read or sub-agent tools differently (the run's JSON lists every tool it called).
- A Windows job for the golden stills in CI (the set is in `tests/golden/windows/`; CI checks Linux only).

- Laptop render estimate on a fresh home's first benchmark. The benchmark times Chrome's start-up
  apart from the frames. Check a cold first estimate against the render on an idle machine and a
  new KIROCUT_HOME with an empty renderer cache. The Modal quote is Modal's rates times container
  time.

- Teardown graphics miss titles on slow-drift videos. look.py can mark a held title as a caption
  when there is no transcript, so the caption band hides it. `drift_dets` needs lettering held
  still for about a second. Thin lettering with no ground over a busy picture may never form a
  box. Tracks from the moving-footage test can pick up photo borders.

Carried over (still untested live):
- Links: OneDrive personal share links go through the `api.onedrive.com/v1.0/shares` download
  path, untested live (no public OneDrive sample). Test with a real share; if Microsoft has
  closed it, say "download it in the browser" instead.
- Measured cost per video on a real run.
- Export opened in DaVinci Resolve (free) to confirm FCPXML positions.

## Needs a decision from the maintainer

- Cutout model licence: RVM is GPL-3.0 (downloaded at first use, never shipped). intake.md lists
  **Yes** first for "Let graphics sit behind you?", so a user who accepts every recommended answer
  downloads it.
