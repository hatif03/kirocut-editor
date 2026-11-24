---
description: Someone downloaded the repo, opened Kiro in it, and the editor skills did not load.
tools: [read, glob, grep, "@kirocut/kirocut_ask"]
dry_run: |
  Eval dry run: this session has no shell tools, and that is expected; do not ask for them. Where a step runs a command, write the exact command in one line, then stop at the next question for the user. The working folder is a fresh download of this folder, and its skills are not in the skill list. Its AGENTS.md (the short version):

  # KiroCut

  KiroCut turns the Kiro IDE into a video editor. Most people who open this folder want to edit a
  video. When the user asks for an edit, drops a video, pastes a link, names a creator, or asks how
  to start:

  1. If the `start` skill is in your skill list, use it. It asks its own questions and runs
     setup, the creator breakdown, the cut and the styled edit in order.
  2. If it is not (the folder was not trusted, so `.kiro/skills/` did not load), ask in the question
     box (kirocut_ask) whether to install the editor, recommended option first. On yes, run
     `kiro-cli powers install` for `plugins/kirocut`, then the same for `plugins/style-match`.
     Then tell the user to start a new Kiro chat and say "edit my video" again.

  If the user is changing this repo itself (skills, scripts, tests, docs), skip the above: follow
  `AGENTS.md`, `docs/BACKLOG.md` and the `improve` skill. To stop the skills loading while you work
  on them, move `.kiro/skills` aside and put it back when you are done.
---
edit my video
