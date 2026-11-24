# The home page

The editor's window. A first run gets setup checks, optional keys, pick a creator, watch
their style get copied, see the style and the skill it became, drop a video. After that it opens on
Home (welcome back), New video (pick clips, then pick a style), Your videos, My style and Settings.
The page only queues jobs. Kiro does every job with the usual skills and reports back, so the page
never decides anything itself.

## How this chat and the window talk

The window and this chat are two ends of one queue. The window queues what the user starts and shows what you
report. You never open a terminal, run a `wait` loop, or ask the user to connect anything. Use the tools:

| To | Call |
|---|---|
| open the window, or one video's review page | `kirocut_open_editor` (pass `edit` for a review page). Put its markdown link in your reply exactly as returned. |
| hear what the user did there (a job, notes sent, Approve) | `kirocut_events` (`wait_s` up to 55) |
| report a job's steps, result, done or failed | `kirocut_report` |
| ask the user | `kirocut_ask`, and `kirocut_answer` for a reply typed in chat |
| answer notes and hand a draft back | `kirocut_scene_*`, `kirocut_review_resolve`, `kirocut_review_round`, `kirocut_review_status` |
| render and follow it | `kirocut_render`, then `kirocut_job` with `wait_s` |

The commands written below as `home.py serve|wait|status` and `review.py serve|wait|round|resolve|status` mean these calls: the same
words, the same arguments. Other scripts (`edit.py`, `plan.py`, the cut's scripts) you still run in the shell.

**The loop.** "Open the home page" (or "edit my video" with no clip): call `kirocut_open_editor`, say in one line that the page
is open, call `kirocut_events` with `wait_s` 55. When it returns a `JOB` line, do that job (below), then call `kirocut_events`
again. An empty result means nothing yet: call it again while the user is expected to act. After about three empty calls in
a row, stop and say: "I'm here. Press what you need in the window, then tell me to continue." The window shows Kiro as
listening only while `kirocut_events` runs; otherwise its **Tell Kiro** button copies a line for the user to paste here. When the
user writes in this chat, a hook adds a line if something is waiting in the window: call `kirocut_events` with `wait_s` 0 first.

**One chat, one video at a time.** A job you take is yours until you report it done or failed. "Separate videos" arrives as one
JOB per clip: do them one by one (for several short clips from one long video, the clips skill runs `clip-editor` agents in
parallel). A taken job with no report for 15 minutes belonged to a chat that stopped: the next `kirocut_report` or
`kirocut_events` adopts it and says `adopted <id>`.

"carry on edits/<name>": the user pressed Send or Approve on a video's review page and Kiro was not listening. Call
`kirocut_open_editor` with that edit, then `kirocut_events` (`wait_s` 0): it returns what the page has, as after any round, with no intake.

## Questions

Ask with `kirocut_ask`. The IDE shows its own form, or the tool returns numbered text to say in your reply; answers come
back to you either way (`kirocut_answer` for a reply typed in chat). The window shows no question cards. A picture the user wants
you to look at arrives as a normal chat attachment. Permission prompts (Allow or Deny for a command) stay in the IDE.

## Keys

The page saves keys itself through `keys.py` (prefix check, one free test request, then the key
file, readable by the user only). A key never reaches the chat, `state.json` or a job line. Never
ask for a key in the chat, and never read the key file. "Skip, add later" runs `setup.py later`.

## The jobs

Progress is automatic: once `kirocut_events` has handed you a job (it is the only thing that takes a queued
one), the long scripts (style-match's, the cut's transcribe, join, build and render,
setup's install-all) post their own steps with a count ("video 3 of 7") onto the job their edit folder
or handle names, and the page shows a live strip with a clock, so it never looks stopped. You still
report the steps you own (the result, `--done`, `--failed`, steps no script covers) with `status`. The
same words as the newest step update that row, never a second one. A new `--step` closes the step before it; `--done` or
`--failed "<plain sentence>"` ends the job:

```bash
kirocut_report job=<teardown|skill|video|setup|update> step="..." [detail="video 3 of 7"] [progress=0.4]
kirocut_report job=<job> result={...} done=true
```

### `JOB teardown @handle platform=<p> take=<parts> [notes=<file>] root=<dir>`

The user pasted a creator and pressed "Copy this style". Run the style-match skill's
**Quick mode** (its SKILL.md) on that handle and platform, in `root`. With `urls=<file>` instead of
a platform, use `list <handle> --urls <file>`. Do not ask the parts question: the page asks it.
With `notes=<likes.md>`, read it first: what the user wrote they like about these videos, and their own
files (example videos, screenshots, PDFs, notes, all in `<root>/references/`). Look closer at what they
named: watch those moments frame by frame, measure them, and say what you found first in `look.md` and in
the style's notes. Read or look at every file. An example video is one more video of the format: pull
frames from it with ffmpeg and compare it with the downloaded ones (fetch.py takes links only).
No Gemini key: skip `gemini.py` (do not offer the key in the chat; the page has it).

The scripts report these steps themselves; use these words if you report one (the page lists the ones still to come):

1. `Listed their videos` (fetch.py list)
2. `Downloaded the top 5 and 2 median` (visual.py download --top 5)
3. `Transcribed every word` (fetch.py transcribe --top 5)
4. `Measured cuts, zooms and camera moves` (visual.py measure)
5. `Reading captions and faces` (look.py measure; `--detail "video N of 9"` as it goes; then format_check.py
   check, and when it leaves videos out its first line as `--detail`)
6. `Naming graphics` (graphics.py measure, gemini.py kinds)
7. `Sound effects and music` (sound.py measure)
8. `Writing the style` (report.py build)

The page reads every number itself from `style-matches/<handle>/style.json` and `videos.json`,
so it fills in as each script writes. `report.py build` also prints the style's skill
(`skill edit-like-<handle> -> <path>`). Then read `look.md` and end the job with what not to copy,
one plain sentence per BAN-level AI tell and per move the teardown rejects:
`--result '{"reject": ["..."]}' --done`. Do not open `teardown.html`: the page links it. The style's
`warnings` (report.py: not one format, graphics on the face) show on the finished analysis and the style page by
themselves; say them in chat as well, and never say something is on the page that the page does not show.

A step that stops: say why with `--failed`, in the words of the skill's "If a script stops" table.

### `JOB skill @handle take=<parts> root=<dir>`

The user ticked what to copy and pressed "Build my skill".

1. `--step "Saving your style"`: `profile.py set 'creators=[{"handle":"<h>","take":[...]}]'`, the
   parts mapped `captions`->captions, `pace`->pace, `graphics` (with `entrances` and `layout`)->visuals,
   `sound` kept for the sound answer (`sound.sfx=true`). Then style-match's
   `editplan.py blend <h>-mine --from <h> --take <parts>`: it refreshes the style's skill
   `edit-like-<h>` on the ticked parts and prints its name.
2. `--step "Checking whether it is a format of its own"`: style-match's
   `references/skill-handoff.md` gate, from the numbers in `look.md` and `videos.json`.
3. Pass: `--step "Writing the skill"`, build it as that file says, link it with
   `python3 "${KIROCUT_PLUGIN}/lib/kirocut/styleskill.py" write style-matches/<h>-mine/style.json --format <name>`,
   then `--step "Testing it with one script"` (its "Finally"). Fail: no format skill; the style and its skill are saved.
4. `--result` then `--done`, the JSON the page shows:

```json
{"passed": true, "check": "5 of 5 top videos use this format, all above their median", "style_skill": "edit-like-handle",
 "name": "format-name", "what": "one sentence: what it edits and how, with measured numbers",
 "use_for": "...", "not_for": "...", "path": "~/.kiro/skills/format-name",
 "prompts": [{"text": "edit my video like @handle", "what": "one line"}],
 "tools": [{"name": "Your photos folder", "why": "one line", "prompt": "use my photos folder for the cards"}],
 "tested": "Kiro wrote one script with it: \"<title>\". 7 beats, 100 words."}
```

A fail sends `{"passed": false, "why": "<which gate question said no>", "style_skill": "edit-like-<h>", "prompts": [...], "tools": [...]}`.
Five prompts, each one the user can paste into Kiro as it is. Every number in `what`,
`check` and `tested` comes from the teardown or the script; leave a field out rather than guess.

### `JOB video <path> as=<mine|@handle|defaults> aspect=<9:16|16:9> edit=<dir> root=<dir>`
### `JOB video takes=<dir>/takes.txt as=... aspect=... edit=<dir> root=<dir>`
### either one with ` script=<edit>/script.md`, ` skill=<skill>`, ` chain=<steps>`, ` sample=1`, ` assets=<edit>/assets.json`, ` broll=<edit>/broll.json`, ` instructions=<edit>/instructions.md` and/or ` mode=broll-reel` before `root=`

The user picked clips and a style and pressed "Make my video" (or "Start the cut" on a first run).
`edit=` is the edit folder the page already made and listed in the library: use it, never make
another. `takes=` lists several clips, one path per line, in the order the user set: they are one
video, so join them first (`cut/references/takes.md`, `join.py <edit>/joined.mp4 <the paths in order>`,
no question: the page asked it). "Separate videos" arrives as one JOB per clip; take them one by one.

`as=` is this video's style only: never `profile.py set creators` for it (only the page's Make default changes the
saved style). The page already wrote `<edit>/style.json` from it (when the job was made, and again when `wait`
handed it to you): skip start step 3's blend, never run `profile.py style` on this edit without `--as <the job's
value>`. `check.py plan` fails when the edit's style is not the one `as=` names. When
`style-matches/<h>/style.json` is not there yet, that creator is still being copied: cut now
(the cut needs no style) and start the styled pass once the teardown job is done.
`aspect`: `profile.py set aspect=<a>`.
The clip's transcription started when the user added it on New video (before Make); `transcribe.py` reuses it.
`script=`: the user added their script on the page. The page wrote it to `<edit>/script.md` (copy it
there if the path is elsewhere). Pass `--script <edit>/script.md` to `transcribe.py`; the cut then runs
`script_match.py` before deciding spans (cut skill step 2).
`skill=`: a skill style (its `style.json` has `"skill"`), see Skill style below.
`chain=`: the style page's "What runs" when it is not the default. With no `chain=`, run logo-pack as usual (after
the cut's approve, before the edit, when the video names two or more products). `chain=none`: never run
logo-pack on this video. `chain=logo-pack,motion` or `chain=motion` (a skill style only): see Skill style below.
`before:<skill>` and `after:<skill>` in `chain=` are skills the user chained onto the style's What runs, in order.
Each `before:` skill runs after the cut's approve, before the edit, on `<edit>/cut.mp4`; each `after:` skill runs
after the final approve, on the finished video, its files into `<edit>/`. Invoke each with the Skill tool (the
editor shows every skill a video ran), say each on the page (`review.py status "Running /<skill>"`), and treat a
skill this session doesn't have as the Skill style section does.
`assets=`: images and links the user added on the page ("Add images or links"; more can come from the editor's
"Anything to add?", and review.py `wait` then prints an `assets:` line). Images are in `<edit>/assets/`. Hand the
file to visual-prep and style-edit: each item goes in first, as a card on its `say` words (else the line it is
about), before anything is searched for.
`instructions=`: the page's "Additional instructions for Kiro", the user's own words about this video. Read the file
before the cut and follow it through every step (the cut, the edit, b-roll, captions, length); it beats a default,
never a rule in `PRINCIPLES.md`. Say on the page what you did with it.
`mode=broll-reel`: the user pasted a reel on New video to copy onto their b-roll ("Copy a reel"). The clip is that reel.
No cut and no style-edit: run the broll-reel skill (`skills/broll-reel/SKILL.md`) on `edit=`, with the job's `broll=` and
`instructions=`. The editor is already open on the reel at the edit stage.
`broll=`: the page's B-roll ticks (`broll.py`): `{"auto", "libraries": [{"name", "folder"}]}`. Hand it to visual-prep
and style-edit. `"auto": true` ("Kiro decides") lists every library: use the ones this video fits (none fits: no
b-roll). `"auto": false`: only the ticked libraries. No `broll=`: no b-roll from the user's folders.

The page already opened the editor on the raw clip when the user pressed Make my video (round 0, "Your
clip, before the cut", `review.json` is there) and lists every step of the cut beside it, ticked as the
scripts report them (review.py `CUT_STEPS`). Serve it and report its URL before transcribing; for `takes=`,
swap in the joined clip after the join:

```bash
R="${KIROCUT_PLUGIN}/lib/kirocut/review.py"
python3 "$R" <edit> start --raw --video <edit>/joined.mp4 --stage cut   # takes= only, after join.py; no review.json: the clip
kirocut_open_editor edit=<edit>      # starts the review page; returns its URL
kirocut_report job=video result={"review_url": "<that URL>"}
```

`serve` opens no browser tab while the home window is showing this job: the home window goes to the
review page in its own tab. Otherwise (no home window, or Kiro alone) it opens a tab. Round 0 has no Approve; notes left on it wait for the cut. Then the start skill from step 2 on, with
this file (or joined.mp4) as the video. The steps
`Joining your clips` (takes only), `Writing down every word`, `Finding retakes and pauses`, `Cutting out
the mistakes`, `Rendering the cut`, `Checking the cut` reach the home page and the editor by themselves
(join.py, transcribe.py, build_timeline.py, render.py, verify_cut.py): never report them yourself. After the cut's approve the style-edit scripts
put their own `--step` on the page's Making the edit card (style-edit `references/review.md`). The cut's
own `start` (cut skill step 6) then opens round 1 on the same page, with the round 0 notes moved onto
the cut: run `wait` and carry on there. `status video --done` once round 1 is up. When that `wait` prints
`EDITS <n> transcript edits applied to spans.json`, the user restored or cut words in the transcript beside the player:
run `build_timeline.py`, `render.py`, `verify_cut.py`, then `review.py <edit> round --video <edit>/cut.mp4`
(`../../style-edit/references/review.md`, Transcript edits).

#### Sample video (`sample=1`)

The user pressed "Try it with a sample video" to see the whole flow before using their own footage. The page
downloaded the repo's public sample take and put its decisions in `edit=`: `words.raw.json`, `spans.json`,
`style.json` (the Card edit sample, cards not behind the head) and `visuals.json`. Do these steps instead of
the start skill's steps 2-4, fast and exact:
ask nothing, never change the profile or the taste, and skip transcribe, `retakes.py propose`, the judge,
verify, visual-prep, logo-pack, the motion skill, music, the render and loudness questions. Notes the user
sends are handled as usual. `C="${KIROCUT_PLUGIN}/skills/cut/scripts"`, `SE="${KIROCUT_PLUGIN}/skills/style-edit/scripts"`.

1. Serve the review page and report its URL, as above.
2. The cut, then `status video --done` and review.py `wait` in the background:

```bash
python3 "$C/build_timeline.py" <path> <edit> && python3 "$C/render.py" <path> <edit> && \
cp <edit>/words.json <edit>/cut.transcript.json && \
python3 "$R" <edit> start --video <edit>/cut.mp4 --stage cut --transcript <edit>/words.json
```

3. On the cut's `APPROVE`: plan and check the stills yourself, then render (no stills round on the page):

```bash
python3 "$C/retakes.py" captions <edit> && node "$SE/capture.mjs" <edit> && \
python3 "${KIROCUT_PLUGIN}/lib/kirocut/run.py" "$SE/face.py" <edit> && \
python3 "$SE/plan.py" <edit>/style.json <edit>/captions.json --aspect 9:16 && python3 "$SE/edit.py" stills <edit>
```

4. Then `python3 "$SE/edit.py" render <edit>` on the laptop, then
   `python3 "$R" <edit> round --stage edit --video <edit>/render.mp4` and `wait`. Say in one line that the
   sample is done and they can drop their own clip on Home next.

#### Skill style

The style points at a skill, so that skill makes the edit instead of style-edit. Cut as usual (start
steps 2-4: the profile, blend and cut still run, so the fallback has the style's numbers). After the
cut's approve run `/<skill>` on `<edit>/cut.mp4`: it makes its own captions, visuals and render. Then
hand its render back as the edit round, as style-edit step 8 does:
`python3 "$R" <edit> round --stage edit --video <its render>`, then `wait` on the page as usual.

`chain=` with `motion` (the user switched Animations on for this skill style): before running `/<skill>`, run the
visual-prep agent on the cut (style-edit steps 1-3), then the motion skill (`motion.py pick`, one clip-builder per
clip, `motion.py check`). Hand `/<skill>` the checked clips: each `motion/<id>/` render with its `beat.json`
times, to lay over the cut on those words. With `logo-pack` in the chain, run logo-pack first and tell `/<skill>`
the logos are in `<edit>/images/` (`logos.json`). Say each step on the page (`review.py status`).

When `<skill>` is not in this session's skill list, never switch silently:
`python3 "$R" <edit> status "This style needs the <skill> skill, which this Kiro session doesn't have"`,
then ask: **Continue with the generic edit, using the style's numbers (Recommended)** / **Stop here**.
Continue: style-edit with `<edit>/style.json` as usual. Stop: `status video --failed "This style needs
the <skill> skill. Open Kiro where that skill is loaded and make the video again."`.

Notes on a skill style's video become rules in that skill's own SKILL.md (`## Learned rules`), never in a
settings file: the final approve's Teach panel does it (`review.py learn --done`), as do `learn --scope this-style` and a
`style-change` job on a skill style, through the skill-improver skill.

### `JOB style-change <my-style|@handle> [style=<style.json>] text=<the user's words>`

The user typed what to change on a style's page (My styles, "Tell it what to change"). Turn the words
into corrections at that style's scope, one per thing they asked, with the taste skill's setting table
(`taste.py add <section> "<rule>" --set <key>=<value>`): `--style <style.json>` for a creator's style
(its `style.overrides.json` and its `edit-like-<slug>` skill), no `--style` for my-style (taste.json
and the `my-style` skill). A wish no setting covers is a word rule at the same scope. Do not ask the
scope question: the page named the style. Report what was saved, in plain words:
`status style-change --step "Saved: captions 6% tall" --result '{"changed": ["Captions 6% tall", "About 3 zooms a minute"]}' --done`.
The page shows `changed` and reloads the style's settings and its "Learned from your feedback" list.
A wish to run another skill on this style's videos ("make a thumbnail after", "run /my-broll before the edit", "stop
running /x") changes its What runs, not a setting: `python3 "$H" chain <style> <skill> --at before|after` (`--off` takes
it out); `<style>` is the job's style (my-style is `mine`). Only a skill this session has.
A text starting `Combined from <name> (<style.json>); ...` came from New style, Combine styles: the new style
started as a copy of the first one. Read each named style.json and set every part the user's words take from
another style (captions, zooms, cut, cards, sound, motion) to that style's values, the same way.
A style card adds "Learned from N videos" once its rules came from N edits (review notes saved at
the final approve's "Teach <style>" panel, `review.py learn --done`).
The same change said in the chat goes through the same `taste.py add`, so both land in one skill.
The page's own controls (sliders, zooms, cut, sound effects) save through `styleskill.learn` directly
and need no job.

### `JOB skill-change <skill> path=<its SKILL.md> text=<the user's words>`

The user pressed "Improve with feedback" on the Skills page and typed what to change in that skill. Run the
skill-improver skill on the words (no video): one short rule per thing they asked, checked with
`skillrules.py similar` (sharpen a twin with `--replace`, ask in the question box when one conflicts), show the
exact lines and ask `Save these (Recommended)` / `Change one` / `Don't save` (the question reaches the page).
After the yes: `skillrules.py add <path> "<rule>" --why "you said: <their words>"`. Then
`status skill-change --result '{"changed": ["<rule>", ...]}' --done` (or `--done` with `{"changed": []}` on
Don't save). The page shows `changed`; the style pages of every style using the skill list the rules.

### `JOB skill-new [text=<what it should do>]`

The user pressed "Make a new skill" on the Skills page. Run the skill-maker skill, with `text` as the answer to
its first interview question when given. Its questions go in the question box (they reach the page). Report
each step with `status skill-new --step "..."`, and at the end
`status skill-new --result '{"summary": "Made /<name>. It is on the Skills page."}' --done`. The new skill
shows on the Skills page, where "Use as a style" makes it a style.

### Connect Modal and Test render (no job for Kiro)

The window runs these itself (`setup.py modal-connect` and `modal-test`), as jobs `modal` and `modal-test`
owned by `home`. `wait` never hands them out and `status` never writes to them.

### `JOB setup`

The user pressed Start setup on the first-run Home. Run `setup.py install-all --report` in the background
(the setup skill's step 0); it reports its own steps onto this job, as in Setup from the page below.

### Update (no job for Kiro)

The window runs Update itself, as job `update` owned by `home`: `update.py market` reinstalls the
`plugins/kirocut` and `plugins/style-match` powers, and the window server restarts from the new
version's folder on the same port with the same token, so the open tab reloads itself. `wait` never hands it out.
An open chat keeps the version it loaded until the user starts a new chat; the page says so.

### `JOB cancel teardown @handle`

The user pressed Stop on that creator's analysing card. Stop that teardown's running commands (`kirocut_job` with `cancel`, or end the shell command),
leave any other analysis running, and say so in one line.

### `JOB cancel <type>` (any other job)

The user pressed the sidebar's Stop on that job. Stop its running commands (`kirocut_job` with `cancel`, or end the shell command), take no next
step, and say so in one line. A Stop also makes every tool call of the session that held the job fail for two
minutes with "The user pressed Stop in the KiroCut window" (the kirocut-window-stop hook): when a tool call fails with that, stop at
once, say in one line what was left unfinished, and wait for the user to write in this chat.

## Setup from the page

A first run opens this page before anything is installed (setup skill step 0), then runs
`setup.py install-all --report` in the background. It reports each step itself
(`status setup --step "Installing the renderer" --progress 0.6`, the share of the whole bar) and ends
with `--done`, or `--failed "<the fixes>"`. Each step also refreshes the page's tool rows. Install
anything else (ffmpeg, Node) the same way: `status setup --step "..."`, then run `install-all --report`
again. A `JOB video` waits for `Ready.`; the page says so too.
