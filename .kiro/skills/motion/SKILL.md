---
name: motion
description: Builds bespoke motion graphics for an edit, one animated clip per beat (HyperFrames + GSAP), each designed for its line and landing on the spoken word, then lays them on the footage through the style-edit render. Picks the beats that need motion (a count, a list, a flow, a before and after, a run, a mechanism), writes a brief per clip, runs one clip-builder agent per clip at once, gates every clip (lint, layout, render, a frame-to-frame motion check, contact sheets), and falls back to the template card for a clip that fails. Use when the user says 'animation', 'motion graphic', 'animate this', 'animate the part where I say X', 'make a clip for', 'build the animations', or when style-edit or visual-prep reaches the beats that need motion. Not for captions or zooms (style-edit), not for real screenshots and logos alone (overlays), not for a product demo film (product-video).
license: MIT
---

# motion

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/motion/SKILL.md` in full before doing anything else.

In that file, `${KIROCUT_SKILL}` means `plugins/kirocut/skills/motion` and `${KIROCUT_PLUGIN}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
