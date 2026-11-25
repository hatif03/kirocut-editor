# KiroCut: what to do next

KiroCut is a video editor for people who make videos. The chat is Kiro. They never learn Kiro.

This plan comes from Kiro's install and Powers docs (pages current as of 20 Nov 2026) and from this repo's setup skill.

## Where this stands (24 Nov 2026)

Phase 1 is built, apart from the proof on a clean machine. The window points at the Kiro chat in this folder: a `kirocut` MCP server
(`plugins/kirocut/mcp/`) gives the chat typed tools for the scene, the editor window, its events, questions and renders; hooks in
`.kiro/hooks/` carry what the user pressed in the window into the chat; nothing opens a terminal for Kiro. What is left of phase 1 is
the IDE spike (`docs/KIRO-COMPAT.md`, about 20 minutes in the IDE) and one sample take run through the chat on Windows and Mac. The
rest of this file is the plan as first written; read "terminal" and "connect" in it as the old route.

## The sentence

KiroCut is a video editor. You talk about the video in the Kiro chat, and you watch, trim, and approve it in a browser tab. Editors and marketers stay in those two places. Kiro is the engine under the chat. Installing KiroCut sets the engine up. Nobody pastes a terminal command, names a plugin, or learns what an agent is.

That sentence is the product. Teaching marketers agentic coding is the wrong frame. The learning curve being removed is ours, not theirs.

Today the sentence is only true for a talking-head cut, and only after a developer-shaped setup. The work below makes the sentence true, then widens the kind of video.

A new sentence does not ship either half. The browser tab already exists: `home.py` serves it on this computer. The `kirocut` command starts `kiro-cli chat` in this folder. The window still has the older connect path beside that. A Kiro Power can install the skills in one click. A Power does not install ffmpeg, Node, or the renderer (about 1.5 GB, 3 GB of disk).

## Do these in order

Each phase has one proof. Do not start the next phase until that proof has happened on a clean machine.

### 1. Make the pitch true

Point the window at the Kiro session in this folder. Retire the connect button and the `kirocut` launch of a separate agent. Keep the job loop in `home.py`.

**Proof.** Open the folder in Kiro, say "edit my video," and finish one talking-head cut in the tab.

Leave for later: new genres, a new renderer, a hosted website.

### 2. One install

Ship two pieces.

- A Kiro Power: `plugin.json` plus the skills, with keywords such as "edit my video."
- One installer for ffmpeg, Node, Python, and the renderer.

Setup progress stays on the tab. Optional keys stay on that tab, never in the chat.

**Proof.** A person who does not write code finishes the sample video without pasting a command.

Leave for later: Kiro Web or mobile. The render stays on the desktop. Kiro Web has no local render.

### 3. Ask what the video is

The first question becomes the job: talking-head (recommended), ad, or something else. Talking-head stays the path that already works. An ad is a thin skill that writes the same `scene.json`.

**Proof.** One real ad is reviewed and rendered in the same tab, with no new editor UI.

Leave for later: a second timeline, a plugin marketplace, or color tools.

### 4. Add genres on the same scene

One skill per genre. An ad is hook, product, offer, end card. A cinematic cut is pace, music, and a look. A social cut is aspect, captions, and pace. Each skill only writes a scene.

**Proof.** Two genres besides talking-head have each shipped one finished video.

Leave for later: the words "any video" on the first screen or the installer.

### 5. Hand it to other people

Public repo. Power install from the GitHub URL (Kiro IDE 1.4.236 or later: Powers, Add Custom Power). Installer for Mac and Windows. A two-minute sample so they can finish without their own footage.

**Proof.** Someone else installs it from the docs and finishes the sample the same day.

Leave for later: teaching people Kiro, VS Code, or the terminal.

## What the package is

A Kiro Power is `plugin.json`, optional skills, and optional `mcp.json`. Install is one click in the Powers panel, or a public GitHub or GitLab URL. Source: [Install powers](https://kiro.dev/docs/powers/installation/) and [Create powers](https://kiro.dev/docs/powers/create/).

| Piece | Who it is for | It covers | It does not cover |
|---|---|---|---|
| Kiro desktop | Already required | The chat, sign-in, opening a folder. Powers in the IDE and on Kiro Web, and in the CLI from v3. | ffmpeg, the renderer, or a video timeline. Kiro Web has no local render. |
| KiroCut Power | The agent | When to edit, how to cut, how to match a style, how to render. Loads when the chat says edit, cut, captions, or ad. | The 1.5 GB of tools. A Power with no installer still ends in brew, winget, or sudo. |
| KiroCut installer | The computer | ffmpeg, Node, Python, the renderer, and a folder they open in Kiro. Progress on the tab they already have. | Teaching the terminal. Optional keys stay on that tab, never in the chat. |
| Browser tab | The person | Watch, trim, notes, approve. This is the only surface an editor or marketer has to learn. | A site they visit with no app installed. The server is local. |

## How the kinds of video grow

The scene file already holds video, images, text, shapes, audio, captions, and cards. The gap is the front door, which still assumes one talking-head take plus 3 to 6 reference videos. New kinds of work are new skills on that scene, not a new app.

| Kind | When | What the chat asks for | What has to exist first |
|---|---|---|---|
| Talking-head | Now | Your video, and 3 to 6 videos edited the same way. | Phase 1, so Kiro is actually listening. |
| Ad | First new kind | Product, offer, length, and footage or a site. | Phase 3. Same review page. |
| Social cut | After one ad has shipped | Aspect, captions, pace, and a long cut or a take. | The ad skill, because it teaches the brief shape. |
| Cinematic | After two genres work | Pace, music, and a look. Grade stays a look, not a color bay. | Proof that skills can change pace and music without a new UI. |

## What professionals should feel

An editor or a marketer opens Kiro because that is where KiroCut lives. The first screen is the video, not a trust prompt, a marketplace, or a doctor log. The chat uses video words: cut the pause, make this an ad, captions smaller. When something is missing, the tab says what is happening and finishes it. The moment a doc says paste this command, the product has asked them to become a developer.
