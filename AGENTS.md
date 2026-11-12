# KiroCut

Skills live under `plugins/kirocut/skills/` and `plugins/style-match/skills/`. Read a skill's `SKILL.md` before doing its work.

| Skill | Use when |
|---|---|
| start | "edit my video", a dropped video, a pasted link |
| setup | a tool is missing |
| cut | "cut my video" |
| style-edit | captions, zooms, cards, the render |
| style-match | "break down" reference videos |
| product-video | a website that should become a film |
| clips | a long video or podcast |
| taste | a correction to an edit |
| improve | turn that kind of feedback into a fix here |

Never ask for an API key in the chat. Keys are saved from the terminal, by the setup skill.

Work in the library (`plugins/kirocut/lib/kirocut/library.py`) or a folder they named. Self-check with `python3 tests/check_plugins.py` and each script's `demo`.
