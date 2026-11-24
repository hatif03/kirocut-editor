---
name: cut
description: Cuts raw talking-head footage into a clean jump cut. Takes one take or several joined (mp4 or mov, any aspect, 4K phone footage is fine), transcribes it word by word, removes retakes, false starts, fillers and dead pauses, and renders cut.mp4 at the source resolution plus words.json timed to the cut. The user approves the cut on a page with the whole transcript and every removed word struck through. Use when the user says 'cut my video', 'just cut it', 'remove my mistakes', 'cut out the retakes', 'remove the pauses', 'clean up this take', 'jump cut this', 'tighten this clip', or asks only for the cut of a raw take; start calls it for a full edit. Runs before style-edit. Not for a general request to edit a video or to make it look like a creator (that is start), not for adding captions, zooms or cards (style-edit), and not for analysing someone else's videos (style-match).
license: MIT
---

# cut

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/cut/SKILL.md` in full before doing anything else.

In that file, `${KIROCUT_SKILL}` means `plugins/kirocut/skills/cut` and `${KIROCUT_PLUGIN}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
