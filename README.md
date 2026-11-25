![](docs/logo.svg)

# KiroCut

Turn your Kiro IDE into a video editor.

Open this folder in [Kiro](https://kiro.dev) and say **edit my video**. KiroCut cuts the retakes, false starts and pauses out of your talking-head take, then styles it: captions, zooms, cards and sound. You approve the cut, then the look, then the render. The editor window opens in your browser. Kiro does the work in this folder.

**Match a style.** Paste 3 to 6 videos edited the same way, or build the look yourself. KiroCut measures the cut, zooms, captions, cards and sound, saves that as a style, and edits your video in it. The references are ones you choose. This repo does not ship example accounts or links to other creators.

It also makes:

- **Shorts from a long video or podcast.** Paste the link. It finds the clips and edits each one.
- **A product video from a website.** Paste the URL. It asks what to show, records the real product and cuts a launch film with its own music.

## Start here

Open the folder in Kiro. Its steering files, skills, agents and hooks load with the workspace, and the `kirocut` tools (an MCP server)
start with it. Say **edit my video** in the chat.

The tools need one file this repo cannot add for you (Kiro keeps `.kiro/settings/` to itself): copy `docs/spike/workspace-mcp.json` to
`.kiro/settings/mcp.json`, or install the Power, which brings its own `mcp.json`. Check with **Kiro: MCP servers** that `kirocut` is connected.

Kiro opens the editor window for you and puts the link in the chat. Press what you need in the window: drop a clip, pick a style,
**Make my video**, leave notes on a draft, **Approve**. Kiro hears it while it waits for you, and when you next write in the chat.
If it is not waiting, the window's **Tell Kiro** button copies a line to paste. Small changes you can just say:
"trim the first 2 seconds", "cut out 0:12 to 0:14", "add a link at the end", "undo that".

**The window.** A sidebar on the left has **+ New video**, **Home**, **Your videos**, **Styles**, your
folders, the video being made right now with its progress, and **Settings**. The panel button folds the
sidebar into a row of icons. To make a video: drop in your clip (or click one you added before), pick a
style, press **Make my video**. Kiro does the work in this chat; its questions come as a form in the IDE, or as numbered
text you answer in the chat.

Where the editor shows depends on your IDE (see [docs/KIRO-COMPAT.md](docs/KIRO-COMPAT.md)): in your browser by default, or
beside the chat in the IDE's Simple Browser or with the small [kirocut-view](extensions/kirocut-view/README.md) extension.

Your videos are saved in one folder, wherever you start: `~/Movies/KiroCut` on a Mac,
`~/Videos/KiroCut` on Windows and Linux. Change it in Settings (or set `KIROCUT_LIBRARY`).

### Other installs

Kiro is the way to open this folder. These also load the same skills:

- Kiro Power: `kiro-cli powers install` the `plugins/kirocut` folder, then `plugins/style-match`. In the IDE: Powers, Add Custom Power, Import power from a folder, and pick each folder.

### Way 1: open this folder in Kiro

**1. Install Kiro** (skip if you have it). Download it from [kiro.dev](https://kiro.dev) and run the installer. Sign in the first time it opens.

**2. Get this folder.** Either:

- **A zip of this folder:** unzip it (double-click on Mac, right-click > **Extract All** on Windows) and open the folder inside.

**3. Open this folder in Kiro.** Choose Open Folder and pick the unzipped folder.

**4. Say yes when it asks whether you trust this folder.** That lets the editor load. Then type
**edit my video**.

**5. Pick "Open the home page".** The editor opens in your browser. Follow
[Getting started](#getting-started) below.

The folder's `.kiro/skills/` and `.kiro/steering/` turn the editor on. If Kiro does not see the skills,
trust the folder and start a new chat.

**Fewer approval prompts.** Kiro asks the first time each command runs. Pick "Yes, and don't ask again",
or put the same rules in `~/.kiro/settings/permissions.yaml` (every project) or in
`~/.kiro/workspace-roots/<this-folder>/permissions.yaml` (this project only; that file stays outside the repo):

```yaml
rules:
  - capability: shell
    match: ["python3 *", "py *", "node *", "ffmpeg *", "ffprobe *", "npx remotion *"]
    effect: allow
```

## Getting started

The first time, the sidebar shows **Getting started** with three steps. It ticks them off as you go
and goes away once your first cut is ready.

1. **Set up.** Press **Start setup**. It checks your computer and installs what is missing: Python,

   ffmpeg, Node, the free transcription model and the renderer (about 1.5 GB, most of it the
    renderer). A home connection is slower than a machine that already has the tools.
    Anything that needs your password, Kiro gives you to paste into your own terminal. While it
    installs, it offers two optional keys (see [Keys](#keys)).
2. **Match a style.** Paste 3 to 6 links to videos edited the same way, or paste a profile and

   tick its videos. Press **Match this style**. Kiro measures them (about 3 minutes, free) and
    saves a style you can rename. The style lists the videos it came from.
3. **Make a video.** Drop in your clip. The new style is already picked. Press **Make my video**.

   No video yet? Pick **Use the sample take**.

Kiro also asks a few questions once (platform, brand, captions, sound). Each is multiple choice and
the first option is fine. The answers are saved in `~/.kirocut/profile.json`.

## Keys

Both are optional and free to start. They make edits better and use less of your Kiro usage.
Skip either and Kiro does that job instead. Add them later by saying **finish setup**.

- **ElevenLabs** transcribes every "um", false start and retake, so the cut is cleaner. Without it,
Whisper transcribes on your computer, which tidies some of those away.
- **Gemini** (Google AI Studio) watches a format's videos and reads its fonts, colours and graphics.

Never paste a key into the chat. Kiro gives you a command that saves it from your own terminal.
Keys live in `~/.config/kirocut/.env`.

## The editor

Each video has an editor page. It opens on the cut, then on each render.

- **Your video beside its transcript.** The transcript follows playback. Struck words were cut.
- **Suggested cuts.** Kiro marks words it thinks should go. Keep them one by one, or press
**Accept all**.
- **Change the cut yourself.** Select words to cut or restore them. **Preview** plays the cut with
your changes. **Apply** keeps them. Undo and Discard are there too.
- **Notes.** Pause anywhere and leave a note. **Send notes** starts the next round. Approve when it
looks right.
- **The look.** After the cut, Kiro makes a sheet of frames from the styled edit. Approve, or say
what to change. You can also move, trim, swap or delete anything by hand.
- **The render.** Kiro times each place to render on your video and shows the cost first. The
render opens on the same page: watch it, leave notes, send them or approve.
- **Teach your style.** When you approve the final video, **Teach your style from this video** turns
your notes into short rules for that style. You see each rule and tick the ones to keep.

A correction you say in the chat ("captions too small", "fewer zooms") is saved to
`~/.kirocut/taste.md` and used on every video after.

## Styles

**Styles** is one list of every style you can edit with. Each card says where it came from: built by
you, learned from your edits, or from a creator's videos. Tabs filter the list: **All**,
**Built by you**, **Matched styles**.

- **Card edit** is a sample style that comes with the editor: real screenshots, logos, photos and
clips on cards behind you, a title pill on the hook, a numbered list, and a red X over a card that
does not apply.
- **New style** opens three choices: **Match a style** (paste 3 to 6 videos), **Build it
yourself** (set captions, zooms, cut, cards and sound), or **Use your own skill** (see below).
- A style's page shows it on your video, with its captions, zooms, cut, cards and sound as options.
Changes save as you go. Make any style your default.
- **Skill styles.** A style can run a Kiro skill instead of using settings. Its card says
"Runs /". Making a video cuts it as usual, then runs that skill on the approved cut and puts
its render on the editor page.
- **Archive** a style from its ⋯ menu to hide it. An **Archived** tab shows up when you have any,
with Unarchive and Delete. **Delete** moves the style to the Trash.
- **Folders** in the sidebar filter your videos and styles. Drag a card onto a folder to file it.
**New folder** is next to New style and at the top of Your videos.

**Your videos** lists every video, with its editor page and a ⋯ menu (Remove from this list, Move to
folder, Download, Move to Trash). **Clear working files** in Settings never deletes your clips, a cut,
a final video or your notes.

Files land in your library folder, or in a project folder you name: `videos/` (clips you dropped in),
`edits/<name>/`, `clips/<name>/`, `product/<name>/` and `style-matches/<handle>/`.

## Skills

The editor is a set of Kiro skills. Three of them help you with your own:

- **logo pack.** Gets the official, brand-colour logo of every company, app and tool named in a video,
checks each one and shows them on one sheet. The edit uses them, and shows logos named together side
by side.
- **skill improver.** Turns a finished video's notes into one-line rules in the style or skill that
made it, after you say yes. It is what **Teach your style from this video** runs.
- **skill maker.** Helps you build your own editing skill. It asks a few questions, runs the task once
without a skill, writes three test cases, drafts the skill, tests it in a fresh agent and fixes it
with you.

For example, say **make a skill** and describe trial reels: short re-cuts of a reel you already
posted, each with a new opening line and hook. skill maker writes the skill and tests it. Then
**New style > Use your own skill** turns it into a style, so every video you make with that style gets
the trial-reel treatment. Your skills live in your own folder and stay when the editor updates.

## Updating

Say **update the editor**. If KiroCut was installed as a power, Kiro runs `kiro-cli powers install` for `plugins/kirocut` and `plugins/style-match`, then asks you to start a new chat.

If you cloned or forked the folder, the same words do the folder update. Kiro makes a backup branch, pulls the
new version in, keeps your changes and runs the self-checks. If they fail, it takes you back to the
backup. It never pushes unless you ask. Settings also shows when an update is ready.

Your styles, skills and settings live in your library folder, not in the plugin, so they stay.

## What you can say

| Skill | Say | You can paste |
|---|---|---|
| `start` | "edit my video", "make my video look like @creator", "new video" | a video file path; a Google Drive, Dropbox or OneDrive share link; a YouTube or TikTok link; a creator profile |
| `setup` | "set up the editor", "finish setup", "add my Gemini key", "set up Modal" | |
| `style-match` | "break down @creator", "tear down @creator" | a TikTok, YouTube or Instagram profile, or single video links |
| `cut` | "cut my video", "remove my mistakes" | a video file path |
| `style-edit` | "style it", "add captions and zooms", "render the edit", "export to Final Cut" (or Premiere, Resolve, CapCut) | |
| `quick-edit` | "trim the first 2 seconds", "cut out 0:12 to 0:14", "add a link at the end", "undo that" | |
| `overlays` | after a render: "add an animation here", "make a diagram of how this works", "this card is wrong", "swap the logo", "show the real page instead", "fewer cards" | |
| `taste` | "captions too small", "fewer zooms" | |
| `logo-pack` | "make a logo pack", "get the logos for this video", "the logos look fake" | |
| `skill-maker` | "make a skill", "create a skill", "turn this into a skill", "help me write a skill" | |
| `skill-improver` | "teach my style from this video", "turn my notes into rules", "make this feedback stick" | |
| `clips` | "clip this video", "make shorts from my podcast" | a long video, a YouTube link, a podcast episode (Apple Podcasts, RSS, YouTube) |
| `trial-reels` | "make trial reels of this", "test other hooks on this reel", "post the trial reels" | an approved reel, or its raw take |
| `product-video` | "make a launch video for my site" | a website URL |
| `update` | "update the editor", "get the latest version", "sync my fork" | |
| `improve` | "improve the editor", "process suggestions" (for people working on this repo) | |

`motion-design` is a reference the other skills read; you do not call it yourself.

A Spotify episode is usually locked: paste the same episode from Apple Podcasts, YouTube or its RSS
feed. An iCloud link opens a web page, not the file: download the video first and give its path.

## What it costs

The editor is free. These are what you may pay for. Numbers marked *estimate* are worked out from
published prices, not measured on a bill.

| Part | Cost | Notes |
|---|---|---|
| Kiro | Your Kiro plan's usage | Not yet measured per video. The keys below lower it. |
| Gemini key (reads a creator's look) | Free | Google AI Studio's free tier, no card. |
| ElevenLabs key (keeps every "um") | Free for a few hours a month | Optional. Without it, Whisper transcribes on your computer for free. |
| Render on your laptop | Free | Often the fastest for a short video. Kiro prints the numbers for your video before you pick. |
| Render on Modal | Quoted from Modal's published per-second rates in `edit.py`, then from the speeds this computer saves after a render. | The Starter plan includes $30 of free credit a month. The first render also builds the render machine once. |
| Render on GitHub Actions | Free | Counts against 2,000 free minutes a month on private repos. |
| Render on AWS Lambda | A few cents to a few dollars (*estimate*) | Your own AWS account, card needed. Not measured yet. Kiro quotes each render first. |

### Cloud renders

- **Modal** (modal.com): your video is split into pieces that render at once on rented machines,
then joined on your laptop. Say **set up Modal**; Kiro walks you through the free account and
logs this computer in.
- **GitHub Actions**: free, no card. Kiro packs the renderer and your footage into a **private**
repo in your account (it asks first), renders on up to 20 machines and downloads the result. Say
**set up GitHub rendering**.
- **AWS Lambda**: many machines at once on your own AWS account. One-time setup of about 20 minutes.
Say **set up Lambda rendering**.

## Your data

- Everything runs on your computer unless you pick a cloud render. After a cloud render your footage
is deleted from the service, unless you said to keep it.
- A product video of a logged-in site uses its own browser profile, never your main one. You log in
by hand, and Kiro asks to delete the login when the video is done.
- Names, emails and account details on screen are blurred by default, your own included.
- It never clicks anything that creates, deletes, pays, publishes or invites unless you said yes
for that video.
- A suggestion you share to help everyone has your names, handles and web addresses removed first.

## Troubleshooting

| Problem                                                             | What to do                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Something is missing or broken                                      | Say **run the editor doctor**. Every line reads `ok`, or `FIX` with the exact command for your computer.                                                                                                                                                                                                    |
| Doctor says something moved off the pinned versions                 | Say **repair the editor setup**. Kiro runs `setup.py repair` from wherever the plugin is installed, and it puts the exact pinned set back. From a cloned folder (Way 1) you can run it yourself: `python3 plugins/kirocut/skills/setup/scripts/setup.py repair` (`py` instead of `python3` on Windows). |
| You skipped a key or step                                           | Say **finish setup**. Only the skipped steps run.                                                                                                                                                                                                                                                           |
| Where do Kiro's questions show up?                                | In the Kiro chat: a form when your IDE can show one, else numbered text you answer in the chat. Permission prompts (Allow or Deny for a command) always show in the IDE.                                                                                                              |
| Kiro does not know "edit my video"                                | The editor is not loaded. Trust the folder and start a new chat, or install the Power (Other installs).                                                                                                                                                                                                                                 |
| `python3` not found                                                 | Mac: `brew install python`. Windows: `winget install -e --id Python.Python.3.12`, then open a new terminal. Linux: `sudo apt install -y python3 python3-venv`.                                                                                                                                              |
| Node is too old on Debian or Ubuntu                                 | Doctor prints the fix: it adds NodeSource's signed package source, then installs Node.                                                                                                                                                                                                                      |
| Chrome or Chromium installed as a Flatpak                           | Only logged-in product videos need your Chrome, and a Flatpak one cannot be used. Install Google Chrome or your distro's `chromium` package; doctor says which it found.                                                                                                                                    |
| A tool installed on Windows is still "not found"                    | Close and reopen Kiro: a `winget` install only shows up in a new terminal.                                                                                                                                                                                                                           |
| `yt-dlp returned nothing`                                           | The site changed. Doctor shows how to update yt-dlp, or paste single video links.                                                                                                                                                                                                                           |
| An Instagram profile fails                                          | Instagram has no free way to list a profile. Paste 10 or more reel links.                                                                                                                                                                                                                                   |
| `Gemini rejected the key`                                           | Make a new key at the link it prints. The teardown carries on without it meanwhile.                                                                                                                                                                                                                         |
| A Drive or Dropbox link fails                                       | Share it as **Anyone with the link**, and link the video file, not the folder.                                                                                                                                                                                                                              |
| `the Modal render failed`                                           | Kiro offers the laptop render instead.                                                                                                                                                                                                                                                                    |
| You logged into a site for a product video and want that login gone | Say **log me out of** . Kiro runs `login.mjs logout <site>`. From a cloned folder (Way 1): `node plugins/kirocut/skills/product-video/scripts/login.mjs logout <site>`.                                                                                                                                 |
| Where are my keys?                                                  | `~/.config/kirocut/.env`, shared by both plugins. With `KIROCUT_HOME` set, `$KIROCUT_HOME/.env` instead, and the shared file is never read.                                                                                                                                                    |

Without Kiro, from a cloned folder (Way 1), one command does the whole install and is safe to re-run:

```
python3 plugins/kirocut/skills/setup/scripts/setup.py bootstrap
```

Every install gets the same versions: Python packages from a hashed lock file
(`plugins/kirocut/requirements/requirements.lock`), Node packages from `package-lock.json`, and
each model checked against its sha256.

## License

This repo is MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

The tools it runs have their own licences:

| Tool | Licence | What it means for you |
|---|---|---|
| [Remotion](https://www.remotion.dev/license) (the renderer) | Remotion License | Free for individuals and for companies of up to 3 people. Bigger companies need a Remotion company licence. |
| [GSAP](https://gsap.com/community/standard-license/) (animation in the renderer, and the `gsap-skills` plugin) | GSAP Standard License | Free, commercial use included, every plugin too. Not an OSI open-source licence. It bans using GSAP in a no-code visual animation builder that competes with Webflow's. |
| [HyperFrames](https://github.com/heygen-com/hyperframes) (the `hyperframes` plugin, and code ported from it) | Apache-2.0 | Free. Ported code keeps HeyGen's copyright, listed in [NOTICE](NOTICE). |

Assets fetched while editing: brand logos from [Simple Icons](https://simpleicons.org) (CC0), icons
from [Lucide](https://lucide.dev) ([ISC licence](https://lucide.dev/license)).

## Contributing

- The rules every video follows, for every user:
[plugins/kirocut/PRINCIPLES.md](plugins/kirocut/PRINCIPLES.md).
- Open this folder in Kiro and say **improve the editor**: the `improve` skill turns the
corrections users marked "would help everyone" into rules, checks and tests here.
- What is next: [docs/BACKLOG.md](docs/BACKLOG.md). What changed: [CHANGELOG.md](CHANGELOG.md).
- In this folder the editor loads from your working copy. To turn the skills off while you work,
move `.kiro/skills` aside and put it back when you are done.
- Run the checks before a pull request:
  ```
  python3 tests/check_plugins.py
  python3 tests/run_demos.py
  python3 tests/check_extension.py
  python3 tests/smoke.py
  ```

  `tests/run_demos.py` runs each script's `demo` (the list is `tests/demos.txt`). After changing a skill or agent run
  `python3 tests/sync_kiro.py`: it rewrites the copies Kiro loads from `.kiro/`. The model evals cost
  money (Kiro CLI, headless); `python3 tests/run_evals.py --runs 1 --case <case>` runs one (RELEASING.md).
