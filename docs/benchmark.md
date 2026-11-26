# Benchmark: a real interview edited in a real reference's style

How close does KiroCut get to a video a person would actually post? `tests/bench/bench.py` measures both videos with
the same code (style-match's measuring scripts) and compares the numbers. This page records the first full run, what it
found wrong with the editor, and what changed.

## The footage

- **The take:** a NASA scientist's unedited answers to eight questions about Artemis II, 8 min 38 s, 1080p, one camera
  (public domain; `tests/bench/takes.json`).
- **The b-roll:** six NASA clips of what she talks about: the crew, the launch, the trajectory, the lunar flyby, the
  Lunar Reconnaissance Orbiter's moon tour, the crew's geology training (public domain, Wikimedia Commons).
- **The reference:** a 15-minute colour-graded travel film the user chose. Measured on this machine and never stored in
  the repo or shown in an example.

## What the reference measures as

| measure | reference |
|---|---|
| cut | every 2.9 s (2.25 cuts every 10 s); hard 66%, whip 9%, zoom punch 8%, match 5% |
| camera | 4.3 zooms, 2.9 push-ins, 3.2 pans a minute |
| speaker on screen | 39% of the time (it cuts away to footage the rest) |
| pauses | up to 2.06 s left in |
| captions | 6 words, one line, sentence case, 1.57% of the long side, cream (#C8BE9A), at the bottom |
| grade | dark (luma 63), warm (+17.6 red over blue in the highlights), contrast 61 |
| sound | music under 100% of it, 17.7 dB under the voice |

## Round 1: the editor as it was

KiroCut cut the take (16 decisions: false starts, stammers, fillers; every pause over 0.3 s tightened; 98.7% of the kept
words heard in the render), styled it in the measured style with 53 b-roll cut-aways on the lines they show, and
rendered it. **5 of 16 measures within 25%.**

| measure | reference | KiroCut | |
|---|---|---|---|
| words a minute | 119 | 205 | the speaker's own pace, tightened pauses |
| cuts every 10 s | 2.25 | 3.89 | +73% |
| median shot | 2.92 s | 1.63 s | -44% |
| longest pause kept | 2.06 s | 0.44 s | -79% |
| zooms a minute | 4.3 | 9.1 | +112% |
| music | 100% of the video | 0% | -100 points |
| caption size | 1.57% | 1.31% | within |
| words per caption | 6 | 6 | same |

Looking at the frames as well as the numbers:

- **The b-roll was a framed card on a flat ground**, where the reference cuts to footage edge to edge.
- **The music was inaudible.** The ducking took the take's room tone (-36 dB) for speech, so the bed stayed 9 dB down the
  whole video.
- **Every sound cue was the same file** (67 of 67), and KiroCut's own check said so.
- **The cut breathed less than the reference:** it tightened every pause to 0.3 s, where this creator lets lines sit
  for up to 2 s.

## What changed in the editor (each with a test)

| found | fix | where |
|---|---|---|
| framed b-roll | a creator's cut-away to a clip fills the frame | `plan.py` `as_scene`, `Scene.tsx` `fullBleed` |
| music held down | the duck's line sits halfway between the take's floor and its voice | `product-video/scripts/sound.py` `speech_gate` |
| one cue file | three takes a cue, rotated | `sfx.py` `TAKES`, `plan.py` `place_sfx` |
| tight pauses | the cut takes the copied creator's pause when the user set none | `build_timeline.py` `pause_target` |
| re-cutting after styling stopped | the style edit's sentence list is not read as pauses | `build_timeline.py` `beat_ranges` |
| the film look | warm, shadows and contrast measured and matched | `look.py` `grade_of`, `plan.py` `grade_for`, `edit.py` `grade_filter` |
| italic serif subtitles | `captions.italic` | `Captions.tsx`, `look.tsx` |
| a 15-minute reference took hours to read | four spread windows | `look.py` `windows` |
| a frame a second with 53 clips | card clips render from proxies (about 7x faster) | `edit.py` `clip_proxy` |
| the render crashed on a missed frame | the cache sized from memory, tabs capped, pieces retried | `render.mjs`, `edit.py` `frame_miss` |
| "every card enters the same way" for cut-aways | only cards over the footage count | `ai_tells.py` |

## Round 2

The second render of the same take with every fix above. Its numbers go here when it is measured.

## What the benchmark cannot see yet

- The reference's "sound effects" are mostly its music's own beats (9% of them land on a cut); the measure counts them
  as effects, so 12 a minute is not a target to copy.
- Its "graphics" are its own footage, read as photos at the top of the frame.
- Its subtitle font cannot be named without the optional Gemini look pass; KiroCut used Cormorant Garamond italic.
- Reading text in frames (RapidOCR on the CPU) takes about 5 s a frame on this laptop.
