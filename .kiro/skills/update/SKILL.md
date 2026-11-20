---
name: update
description: Updates KiroCut to its newest version. Works out how it was installed and does the right thing for each. The official plugin from the marketplace gets the plugin update commands for kirocut and style-match. A fork the user owns (the power-user route, where they change the editor's own code) gets its new versions pulled from the upstream remote and merged with their changes kept, after a backup branch, then the fast self-checks, with a rollback if they fail. A plain clone gets the fork route in three steps. Use when the user says 'update the editor', 'get the latest version', 'sync my fork', 'pull the new version', or asks how to stay up to date after changing the editor's code. Not for changing a style or a setting (that is taste or the home page), and not for maintainers turning feedback into fixes (that is improve).
license: MIT
---

# update

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/kirocut/skills/update/SKILL.md` in full before doing anything else.

In that file, `${CLAUDE_SKILL_DIR}` means `plugins/kirocut/skills/update` and `${CLAUDE_PLUGIN_ROOT}` means `plugins/kirocut`. Those paths start at the root of this repo. They are not the folder this file is in.
