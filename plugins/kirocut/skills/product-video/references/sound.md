# Sound: what Linear's and Apple's films do, and what sound.py takes

What `sound.py` builds for each mood.

## Linear

| film | LUFS | music | voice | notes |
|---|---|---|---|---|
| Introducing Linear Agent (55 s) | -28.9 | ambient bed | none | sub swells at 3-5 s and 41-43 s, UI ticks only at 7.5-11.7 s and 17.9-20.6 s |
| Releases trailer (30 s) | -24.7 | 110 BPM, a sub hit every bar (2.18 s apart) | none | chord change every 4 bars (9.0 s, 18.0 s); pulse stops at 27 s, pads ring to silence by 30 s |
| Releases, Initiatives demos | -21.1, -25.4 | none | yes | silence (-78 dB) between sentences: no bed under the voice |

- **Warm and dark.** 25-32% of the energy under 90 Hz, 40% in 300-3000 Hz, almost nothing over 4 kHz.
  Spectral centroid 750-810 Hz. No hi-hats, no claps.
- **The pulse is a sub, once a bar**, about 110 BPM. Pads hold 300-1000 Hz and change chord every
  2-4 bars.
- **Sound effects are rare and earned**: 0.3-0.4 high transients a second over a whole film, all of
  them while the UI is acting (typing ticks about 0.4 s apart). None on cuts.
- **Sub swells mark the big reveals**, about 2 in 55 s.
- **Ending**: the pulse stops on the logo; the pads ring out to silence over 3-5 s. No hit.
- Mixed quiet for YouTube (-25 to -29 LUFS). For social we master to -14.

## Apple

- **Loud, rhythmic, voice-led**: -15.5 to -16.1 LUFS. Creator Studio: 120 BPM, cuts within 2-4
  frames of the beat (1.63, 3.25, 9.72 s against beats at 1.7, 3.2, 9.7 s).
- **Hard button ending**: the music stops dead on the last beat and the logo sits in silence 4-5 s.
- Under voice, the bed in the gaps between sentences sits about 8 dB under the speech.

## Stripe, Arc, Raycast (style families)

- Stripe: -11 to -14 LUFS, music only, 90-96 BPM four-on-the-floor, a dropout about 3 s before the
  end, then the logo sting.
- Arc: -10.5 to -11.5 LUFS, 92-144 BPM, bells and arpeggios, 1 s of silence before a bass drop on the
  reveal, thin UI ticks on colour flips, rings out.
- Raycast: -13.2 LUFS, ambient pad and sub swells in 2-4 s blocks, no drums, key ticks under typing,
  fades to a low tail.

## What sound.py does with it

| | linear (default) | apple | stripe | arc | raycast |
|---|---|---|---|---|---|
| BPM | 110 | 120 | 100 | 96 | 128 |
| pulse | sub, bar downbeat | sub on 1 and 3, 8th ticks | sub, bar | sub on 1 and 3 | sub every beat, 8th ticks |
| plucks | 8ths from bar 3 | 8ths | 16ths, glassy | 8ths, major | 16ths |
| ending | pulse stops, resolved chord rings out | button: stops dead | rings | rings | button |

- **The score follows the cut.** Each story beat is a section: the hook and reveal get the
  pads alone, the actions and results the groove (sub pulse, bass line, brushed ticks under 3.5 kHz,
  plucks), the payoff the fullest (brighter pads, a busier bass), the end the resolved chord. The chord
  changes where a beat starts (snapped to the nearest beat) and every 2 bars inside a long one; the pads
  are voice-led (each voice moves to the nearest note of the next chord); the bass plays the root on
  the change, the fifth and octave in the bar and steps into the next chord's root; the pads dip 18%
  after each sub and recover (they breathe with the pulse); a riser (air climbing in band, two tones
  gliding up an octave) lands on the payoff with a sub; the last chord before the logo is the
  progression's approach chord, and the end rings the tonic in major with a 9th over a low tonic and
  one soft bell. Hi-hats only in the apple and raycast moods.
- **Cuts land on the beat.** `product.py plan` snaps every shot end to the score's beat grid (the
  user's own track: its detected beats), and the pads lift slightly for half a second after each cut.
- **Sound effects only where the UI acts**: a soft click on every recorded click and key press, a tick
  per typed character (9 a second, as recorded), a whoosh into a whip, a push-through or a lift, a
  swell and a sub hit into the logo. Never on a plain cut.
- **One file**: music, effects and any voice are mixed in numpy, the music ducked 9 dB under a voice,
  then mastered by ffmpeg to -14 LUFS integrated with a -1 dBTP ceiling (limited at 4x oversampling,
  measured -1.6 dBTP). Remotion plays it at unity.
- Every sound is synthesised in `sound.py` (`../audio/LICENSES.md`): nothing to licence, nothing
  downloaded.
