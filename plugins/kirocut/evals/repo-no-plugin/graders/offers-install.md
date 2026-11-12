---
type: llm
focus: trace
---
The editor skills are not loaded in this session. PASS only if all three hold:
1. Kiro asks the user whether to install the editor before installing anything, with concrete choices (yes first), through AskUserQuestion or as a short list of options in its reply.
2. It names the install commands: `kiro-cli powers install` for `plugins/kirocut` and `plugins/style-match`.
3. It says what comes after the install: a new Kiro chat, then the edit begins with the `start` skill (or the user says "edit my video" again, which starts it).
FAIL if it tries to edit the video without the skills, asks for the video first, runs or claims to run the install without asking, or never says how the edit starts after installing.
