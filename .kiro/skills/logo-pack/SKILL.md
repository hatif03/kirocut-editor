---
name: logo-pack
description: Builds clean brand-colour logos for every company, app or tool named in a video. Lists the names from the edit's transcript, fetches each brand's own logo (SVG first, else a large PNG) with the editor's logo code, trims it, makes a transparent 512 px PNG beside the SVG, checks each one (official, transparent, sharp, brand colours) and fixes the failures, then notes the logos named together so the edit shows them side by side. Writes the files style-edit already reads (images/logo-<brand>.svg|png) plus logos.json. Use when the user says 'make a logo pack', 'get the logos for this video', 'official logos for the apps I mention', 'the logos look fake' or 'logos in their real colours', or before style-edit on a video that names two or more products. Not for moving or swapping one card in a rendered edit (overlays), and not for screenshots of a page (style-edit captures).
license: MIT
---

# logo-pack

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/logo-pack/SKILL.md` in full before doing anything else.

In that file, `${CLAUDE_SKILL_DIR}` means `plugins/kirocut/skills/logo-pack` and `${CLAUDE_PLUGIN_ROOT}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
