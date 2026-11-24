---
name: improve
description: For the editor's maintainers. Turns what users corrected into lasting fixes in this repo, for every user, enforced by code and tests rather than notes. Reads the suggestions users marked 'would help everyone' (~/.kirocut/suggestions.jsonl), taste rules said twice (taste.py report), preview corrections (edits/*/corrections.jsonl), review-page notes (*/review.json) and open GitHub issues labelled feedback; groups repeats; for each item the maintainer accepts, writes the general rule into PRINCIPLES.md and the skill that owns it, adds or tightens the check that enforces it, adds a test that fails before and passes after, runs the full test set and leaves a CHANGELOG.md entry to commit. Use when the maintainer says 'improve the editor', 'turn feedback into fixes', 'process suggestions', 'what are users complaining about', 'go through the feedback issues'. Not for one user's own preferences (that is taste), and not for editing a video.
license: MIT
---

# improve

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/improve/SKILL.md` in full before doing anything else.

In that file, `${KIROCUT_SKILL}` means `plugins/kirocut/skills/improve` and `${KIROCUT_PLUGIN}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
