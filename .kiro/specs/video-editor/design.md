# Design

## Overview

Kiro is the agent. The editor window is a local Python server. Skills are markdown plus scripts. Footage stays in the library folder.

```
Kiro  →  start skill  →  setup, cut, style-edit
                ↓
         home.py / review.py  (the window)
                ↓
         library: edits/<name>/
                ↓
         Remotion render
```

## Components

- `plugins/kirocut/skills/start/SKILL.md` routes a file, a link, or "edit my video".
- `plugins/kirocut/skills/setup/` checks Python, ffmpeg, Node and the renderer.
- `plugins/kirocut/skills/cut/` proposes the cuts.
- `plugins/kirocut/skills/style-edit/` plans captions, zooms and cards and calls Remotion.
- `plugins/kirocut/lib/kirocut/home.py` serves `home.html`.
- `plugins/kirocut/lib/kirocut/review.py` serves `review.html`.
- `plugins/kirocut/lib/kirocut/library.py` resolves where videos are stored.

## Brand surfaces

The name and mark are set in `docs/logo.svg`, the `<title>` and sidebar of `home.html`, and the rail of `review.html`. Steering in `.kiro/steering/brand.md` is the rule for later copy.

## Error handling

A missing tool is a setup step, not a crash. A failed cloud render falls back to the laptop. Keys are never typed into the chat.
