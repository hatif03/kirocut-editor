---
name: setup
description: Installs and checks everything KiroCut needs on Mac, Windows or Linux (Python, ffmpeg, Node, git, the Python packages, the free transcription model and the Remotion renderer): on a first run it opens the editor's window first, then installs in the background. Then saves the user's style once. Also walks through the optional API keys (Gemini for reading a creator's look, ElevenLabs for verbatim transcripts), the optional CrisperWhisper model, cloud renders on Modal ($30 free credit a month), the GitHub CLI for free GitHub Actions renders and AWS Lambda. Use when the user says 'set up the editor', 'install kirocut', 'setup', 'finish setup', 'set up Modal', 'cloud renders', 'add my Gemini key', 'add my ElevenLabs key', when they have just installed the plugin, or when another kirocut or style-match step fails because a tool is missing. Not for editing a video (that is start) and not for changing one edit preference (that is taste).
license: MIT
---

# setup

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/setup/SKILL.md` in full before doing anything else.

In that file, `${KIROCUT_SKILL}` means `plugins/kirocut/skills/setup` and `${KIROCUT_PLUGIN}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
