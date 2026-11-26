---
inclusion: always
---

# Editing from the chat

The user edits video by talking here and by pressing things in the editor window. Use the `kirocut` tools, not shell commands, for anything they cover.

- Start a session with `kirocut_status`. If it says a tool is missing, run the setup skill before anything else.
- A whole new edit ("edit my video", a dropped clip or link): the start skill. A one-line change to a video that already has an edit ("trim the first 2 seconds", "add a link at the end", "undo that"): the quick-edit skill. Never run the whole edit again for a small change.
- Show the editor with `kirocut_open_editor` and put the link it returns in your reply as written. Then `kirocut_events` hears what the user pressed. Between your turns a hook adds a line when something is waiting there.
- Change a video only through the scene: read with `kirocut_scene_show`, change with `kirocut_scene_ops` or `kirocut_scene_add`, check with `kirocut_stills`, and say what changed in one line. Every change is undoable (`kirocut_scene_undo`).
- Questions go through `kirocut_ask`. Never ask for an API key in the chat: the setup skill gives a command for the user's own terminal.
- Long work (a render) is `kirocut_render` and `kirocut_job`. Say what is running and how long it will take; never leave the user in silence.
- Let the user watch: for a new edit, call `kirocut_open_editor` with `edit` and `source` (the raw take) before the cut starts, so the page plays it, ticks off each step and strikes the words as you cut. "Show me how you edited it": `kirocut_replay`.
- A first `kirocut_status` on a new machine starts installing what KiroCut can install itself (`setup_job`): tell the user, open the editor, and follow it with `kirocut_job`.
- A correction the user gives about how they like videos is a rule: change the video first, then save it with `kirocut_taste` (the taste skill).
