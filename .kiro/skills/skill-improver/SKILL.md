---
name: skill-improver
description: Turns the feedback on a finished video into lasting rules in the style or skill that made it. Collects the video's notes (review-page notes, preview fixes, chat corrections), keeps only the ones meant for every future video, finds the style or skill behind the edit, checks for a similar rule and sharpens it instead of adding a twin, writes each rule as one short line with its reason and date, shows the exact lines and file, and saves only after the user says yes. A skill style (style.json 'skill') gets the rules in that skill's SKILL.md under '## Learned rules' with a short log; a settings style gets them in its own rules and overrides. Runs the review page's 'Teach your style from this video'. Use when the user says 'teach my style from this video', 'turn my notes into rules', 'make this feedback stick', 'update my editing skill from this video' or 'learn from this video's notes'. Not for one correction said in the moment (taste), and not for fixing the editor for every user (improve).
license: MIT
---

# skill-improver

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/skill-improver/SKILL.md` in full before doing anything else.

In that file, `${KIROCUT_SKILL}` means `plugins/kirocut/skills/skill-improver` and `${KIROCUT_PLUGIN}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
