---
name: quick-edit
description: Makes a small change to a video that already has a cut or a styled edit, straight from chat, with no intake and no re-run of the whole edit. Trims or cuts a range, adds, moves, resizes or removes text, pictures, logos and sounds, changes caption size or position, undoes the last change. It reads the scene, changes it with one tool call, looks at a still, and says in one line what changed. Use when the user says "trim the first 2 seconds", "cut out 0:12 to 0:14", "add a link at the end", "put the logo top right", "move the title up", "undo that", or asks for any other one-line change to a video that is already made. Not for a first cut of raw footage (cut), not for a whole new look (style-edit), and not for notes sent from the review page (start's home.md, the review loop).
license: MIT
compatibility: Needs the kirocut MCP tools (kirocut_scene_show, kirocut_scene_ops and the others) and an edit that has been opened in the editor once. ffmpeg and the renderer only for stills and export.
---

# Quick edit

Paths: `${KIROCUT_SKILL}` means the folder containing this SKILL.md, and `${KIROCUT_PLUGIN}` the plugin folder two levels above it (`plugins/kirocut` here).

One small change, done now, shown, and easy to take back. The video is a scene (`lib/kirocut/SCENE.md`): every thing on screen
is an item, and a change is an op on it. Never re-plan, re-render or rebuild the edit for a one-line change.

Ask a question (`kirocut_ask`) only when two videos or two items fit the words equally. Otherwise act, then say what you did.

## 1. Which video

The one the user named, else the one in this chat's last step. If neither: `kirocut_library` with `status` ready or making;
the newest one is almost always right. Say its name in your answer so a wrong guess is easy to catch.

## 2. Read before you change

`kirocut_scene_show` with the edit (and `at`, the second the user named: it lists only what is on screen then, the words
around it and the pauses). Use the real item ids and times it returns. When it says this draft is not a scene, call
`kirocut_open_editor` with the edit once (the page makes the scene) and read again.

Times the user says are the video's: "0:12" is 12 seconds on the page's timeline, which is what `kirocut_scene_show` shows.

## 3. Change it

One `kirocut_scene_ops` call per request, with a `why` of a few words (the page shows it next to the change). The common
requests:

| The user asks for | Op |
|---|---|
| trim the first N seconds | `{"op":"trim","item":<first footage clip>,"edge":"start","by":N}` |
| trim the last N seconds | `{"op":"trim","item":<last footage clip>,"edge":"end","by":-N}` |
| cut out A to B (a pause, a mistake) | `{"op":"cut","start":A,"end":B}`: later items move up by itself |
| bring back what was cut | `trim` the clip's edge outward by the cut's `dur` (the cut is in `cuts`) |
| add text at T | `kirocut_scene_add` type `text`, `text`, `start` T, `end` T+2.5, `y` 1500 for the lower third |
| put a picture or logo somewhere | `kirocut_scene_add` type `image`, `src` the file, `start`, `end`, `x` `y` `w` |
| move, resize, retime an item | `{"op":"set","item":id,"props":{"x":..,"y":..,"w":..}}` or `start` `end` |
| change a text | `{"op":"set","item":id,"props":{"text":"..."}}` |
| remove an item | `{"op":"remove","item":id}` |
| a sound at T | `kirocut_scene_add` type `audio`, `src`, `start` |
| louder or quieter | `{"op":"set","item":id,"props":{"volume":1.5}}` (1 is as recorded, 0 silence) |
| captions bigger, higher, fewer words a line | `set` the captions item's `style` with the whole dict from `kirocut_scene_show`, the one key changed (`size_pct`, `y_pct`, `words_per_caption`) |
| a punch-in here | `scale` keys on the footage clip: `{"op":"set","item":clip,"props":{"keys":{"scale":[[0,1,"inout"],[0.6,1.15,"hold"]]}}}`, times from the clip's start |
| hide, mute or lock a whole track | `{"op":"track","track":id,"props":{"hidden":true}}` |

Placement rules: an item stays inside x 60 to 940 and y 250 to 1440 of a 1080 by 1920 canvas (the app bars cover the rest), never
over the speaker's face (`face.json` in the edit has the head box), and a new text goes in the same font and size as the
others on screen. A locked item or track takes no change: say so, and ask before unlocking.

## 4. Look, then say

For anything you can see (text, a picture, captions, a punch-in), `kirocut_stills` at a time the change shows, and look at the
image. Fix what is wrong first (text over the face, cut off at the edge, unreadable). Then one line to the user: what changed,
where (the time), and "say undo that to put it back". If the editor page is open it already shows the change.

## 5. Undo, redo, and which change

"Undo that" is `kirocut_scene_changes`, then `kirocut_scene_undo` with the number of the newest change that is not undone.
"Put it back" after an undo is the same call with `redo`. The user's own page edits since stay. An older change by number works the same way.

## 6. When it is a preference, not just this video

A request that reads as lasting ("always", "every video", "I never want") is also a rule: do the change here, then save it with the
taste skill. A one-off is only this video. Say which you did.

## 7. Render only when asked

The page plays the scene live. Make the file when the user asks for it: `kirocut_render` (mode export), then `kirocut_job` with
`wait_s` to follow it; say where the file is. After a plan render (a render.mp4 from style-edit), a small card or text move can be
`kirocut_render` mode patch instead of a full render.

## If it does not work

| It says | Do |
|---|---|
| item not found, or the id changed | `kirocut_scene_show` again: ids are the page's, a split makes new ones |
| split outside the item, or shorter than a frame | use a time inside the clip, at least one frame from its edge |
| the item or track is locked | tell the user; unlock only if they say so |
| `no_such_edit` | `kirocut_library` and use the exact name |
| the edit has no scene yet | `kirocut_open_editor` with the edit, then read again |
