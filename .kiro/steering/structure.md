---
inclusion: always
---

# Structure

```
.kiro/                         steering, specs, hooks, agents, skills (this IDE; skills and agents are generated)
AGENTS.md                      same instructions for every agent (GEMINI.md is a copy)
plugins/kirocut/             editor skills, the window, the renderer
  lib/kirocut/               home.py, review.py, library.py, links.py, scene.py, kirohook.py
  mcp/                         the kirocut MCP server (server.py, tools_*.py), launch.mjs, compat.json
  agents/<name>.md             sub-agents (copied to .kiro/agents/ by tests/sync_kiro.py)
  skills/<name>/SKILL.md       one skill per folder
extensions/kirocut-view/       optional IDE panel for the editor (installed by hand)
  remotion/                    renderer
  presets/styles/              sample styles shipped with the editor
plugins/style-match/      measures a set of reference videos into a style
tests/                         check_plugins.py and the other self-checks
docs/logo.svg                  KiroCut mark
```

## Names

- Skill folders stay kebab-case and match the `name` in `SKILL.md`.
- An edit lives at `edits/<name>/` in the library. A measured style lives at `style-matches/<handle>/`.
- User-facing strings say KiroCut. The powers are `kirocut` and `style-match`. The terminal command is `kirocut`. The Python package is `kirocut`, in `plugins/kirocut/lib/kirocut`.

## Where work goes

A video the person is editing is written in the library or a project folder they named, not into `plugins/`. A change to the editor itself (skills, scripts, tests, docs, this `.kiro` folder) stays in the repo.
