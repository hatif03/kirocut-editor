---
name: taste
description: Remembers how the user likes their videos edited, so they never give the same correction twice. Saves every correction or preference about an edit (the cut, captions, visuals, sound, layout) into ~/.kirocut/taste.md as a plain rule, and into taste.json when it maps to a setting the scripts read (pause length, fillers, caption size, words per caption, zooms, sound, layout), deduplicated, scoped to every video or just this one, and counted when applied; one that would help everyone goes to the maintainers. Every other KiroCut skill reads both before it starts. Use whenever the user reacts to an edit ('too slow', 'captions are too small', 'fewer zooms', 'I hate the whoosh', 'that's perfect, keep it like that'), and when they ask 'what do you know about my taste', 'show my settings', 'forget that rule' or 'are you learning'. Also learns how they cut from a raw take and their posted version ('I already edit by hand', 'learn from my edit'). Not for a finished video's notes as a batch (skill-improver).
license: MIT
---

# taste

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/taste/SKILL.md` in full before doing anything else.

In that file, `${CLAUDE_SKILL_DIR}` means `plugins/kirocut/skills/taste` and `${CLAUDE_PLUGIN_ROOT}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
