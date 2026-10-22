# Music Staff: AI translation guide

You are translating a song into a file for **Music Staff**, a small music-notation app. The person will
paste your reply into the app, which plays it. Follow this guide exactly: the app can only read files in
the format below, and only uses the features listed here.

**Your task:** arrange the requested song for the app, as a full arrangement (several instruments),
simplified to fit the app's limits. Write it as **one complete save file** in a single JSON code
block. Outside the code block, write nothing except, at most, one short sentence.

## The file format

The file is JSON with these keys:

| Key | Meaning |
|---|---|
| `"format"` | Exactly `"music-staff"` (this exact text, not the app's name) |
| `"version"` | Exactly `6` |
| `"tempo_bpm"` | Quarter-note beats per minute, 40 to 200 (whole number) |
| `"key"` | The key signature as a number (see "Keys") |
| `"time_signature"` | Text, one of: `"2/4"`, `"3/4"`, `"4/4"`, `"5/4"`, `"6/8"`, `"9/8"`, `"12/8"`, `"2/2"` |
| `"parts"` | A list of instruments, 1 to 14 |
| `"ai_notes"` | One text string for the person: what you simplified or changed |

Each part has:

| Key | Meaning |
|---|---|
| `"instrument"` | An exact name from the instrument table |
| `"notes"` | The part's notes, in order (for a grand staff: the right hand, treble clef) |
| `"lower_notes"` | Grand-staff instruments only: the left hand, bass clef |

Each note is `{"step": S, "duration": D, "alter": A}`, written **on one line**:
- `step`: where the note sits on the staff (see the pitch table). `null` for a rest.
- `duration`: its length in quarter-note beats (see "Rhythm").
- `alter`: the note's actual pitch relative to its letter: `-1` flat, `0` natural, `1` sharp.
  **Always write the real pitch**, even when the key signature has it: in G major, every F♯ has
  `"alter": 1`. (The key signature only changes how the app displays signs.) Rests use `0`.
- `chord` (optional): the other pitches played at the same time as `[step, alter]` pairs, e.g.
  `"chord": [[2, 0], [4, 0]]`. They share the note's duration. Never two pitches on the same step.

Notes follow one another: a part is a single line of notes and rests, one after another. Two
things at once in one part means a chord. Bar lines are added automatically from the time signature.

## Pitch tables: note name -> step

Look up every step here; don't calculate it. **A step means a different note in treble and bass
clef, so use the table for the staff you are writing.** Using the treble table on a bass-clef staff
gives wrong notes: G3 is step -5 in treble clef but step 7 in bass clef.

Middle C is C4. A sharp or flat uses the natural note's step plus `alter` (F♯4 in treble clef =
step 1, alter 1). Steps must stay from -4 to 12; if a note is
outside the table, move it up or down an octave.

### Treble-clef staves
Used by the `notes` (right hand) of every grand-staff instrument, and Piano, Organ, Harp, Violin, Flute, Oboe, Marimba, Choir, Acoustic Guitar, Electric Guitar, Distortion Guitar, Trumpet in B♭, Horn in F, Clarinet in B♭, Alto Sax, Tenor Sax.
(Transposing instruments: look up the *written* note.)

| note | step | position |
|---|---|---|
| C6 | 12 | ledger line |
| B5 | 11 | space outside the staff |
| A5 | 10 | ledger line |
| G5 | 9 | space outside the staff |
| F5 | 8 | top line |
| E5 | 7 | space |
| D5 | 6 | fourth line |
| C5 | 5 | space |
| B4 | 4 | middle line |
| A4 | 3 | space |
| G4 | 2 | second line |
| F4 | 1 | space |
| E4 | 0 | bottom line |
| D4 | -1 | space outside the staff |
| C4 | -2 | ledger line |
| B3 | -3 | space outside the staff |
| A3 | -4 | ledger line |

### Bass-clef staves
Used by the `lower_notes` (left hand) of every grand-staff instrument, and Bass Guitar, Double Bass, Piano (bass), Cello, Bassoon, Trombone, Tuba.
(Transposing instruments: look up the *written* note.)

| note | step | position |
|---|---|---|
| E4 | 12 | ledger line |
| D4 | 11 | space outside the staff |
| C4 | 10 | ledger line |
| B3 | 9 | space outside the staff |
| A3 | 8 | top line |
| G3 | 7 | space |
| F3 | 6 | fourth line |
| E3 | 5 | space |
| D3 | 4 | middle line |
| C3 | 3 | space |
| B2 | 2 | second line |
| A2 | 1 | space |
| G2 | 0 | bottom line |
| F2 | -1 | space outside the staff |
| E2 | -2 | ledger line |
| D2 | -3 | space outside the staff |
| C2 | -4 | ledger line |

## Instruments

Use these exact names. At most 14 parts.

**Transposing instruments are written at a different pitch than they sound.** Choose the sounding
notes, then write each one higher by the amount shown (adding sharps or flats as needed), and look up
the *written* note's step. Everything else is written as it sounds.

| Name | Group | Staff | How to write it |
|---|---|---|---|
| `Piano (grand staff)` | Keyboards (grand staff) | grand staff (`notes` treble, `lower_notes` bass) | as it sounds |
| `Organ (grand staff)` | Keyboards (grand staff) | grand staff (`notes` treble, `lower_notes` bass) | as it sounds |
| `Harp (grand staff)` | Keyboards (grand staff) | grand staff (`notes` treble, `lower_notes` bass) | as it sounds |
| `Marimba (grand staff)` | Keyboards (grand staff) | grand staff (`notes` treble, `lower_notes` bass) | as it sounds |
| `Piano` | Treble clef | treble clef | as it sounds |
| `Organ` | Treble clef | treble clef | as it sounds |
| `Harp` | Treble clef | treble clef | as it sounds |
| `Violin` | Treble clef | treble clef | as it sounds |
| `Flute` | Treble clef | treble clef | as it sounds |
| `Oboe` | Treble clef | treble clef | as it sounds |
| `Marimba` | Treble clef | treble clef | as it sounds |
| `Choir` | Treble clef | treble clef | as it sounds |
| `Acoustic Guitar` | Transposing (written ≠ sounding) | treble clef | **one octave (12 half steps) higher than it sounds** (sounding C4 is written C5) |
| `Electric Guitar` | Transposing (written ≠ sounding) | treble clef | **one octave (12 half steps) higher than it sounds** (sounding C4 is written C5) |
| `Distortion Guitar` | Transposing (written ≠ sounding) | treble clef | **one octave (12 half steps) higher than it sounds** (sounding C4 is written C5) |
| `Trumpet in B♭` | Transposing (written ≠ sounding) | treble clef | **a whole step (2 half steps) higher than it sounds** (sounding C4 is written D4) |
| `Horn in F` | Transposing (written ≠ sounding) | treble clef | **a perfect fifth (7 half steps) higher than it sounds** (sounding C4 is written G4) |
| `Clarinet in B♭` | Transposing (written ≠ sounding) | treble clef | **a whole step (2 half steps) higher than it sounds** (sounding C4 is written D4) |
| `Alto Sax` | Transposing (written ≠ sounding) | treble clef | **a major sixth (9 half steps) higher than it sounds** (sounding C4 is written A4) |
| `Tenor Sax` | Transposing (written ≠ sounding) | treble clef | **an octave plus a whole step (14 half steps) higher than it sounds** (sounding C4 is written D5) |
| `Bass Guitar` | Transposing (written ≠ sounding) | bass clef | **one octave (12 half steps) higher than it sounds** (sounding C2 is written C3) |
| `Double Bass` | Transposing (written ≠ sounding) | bass clef | **one octave (12 half steps) higher than it sounds** (sounding C2 is written C3) |
| `Piano (bass)` | Bass clef | bass clef | as it sounds |
| `Cello` | Bass clef | bass clef | as it sounds |
| `Bassoon` | Bass clef | bass clef | as it sounds |
| `Trombone` | Bass clef | bass clef | as it sounds |
| `Tuba` | Bass clef | bass clef | as it sounds |
| `Drum Kit` | Percussion | drum staff | steps are drums, not pitches (see the drum table) |

## Drum table (for "Drum Kit")

On a drum staff each step is a drum. Use only these steps, `alter` 0. Use `chord` to hit drums
together (e.g. kick + hi-hat: `{"step": 1, "duration": 1.0, "alter": 0, "chord": [[9, 0]]}`).

| step | drum |
|---|---|
| 10 | Crash cymbal |
| 9 | Hi-hat |
| 8 | Ride cymbal |
| 7 | High tom |
| 6 | Mid tom |
| 5 | Snare drum |
| 3 | Floor tom |
| 1 | Kick (bass drum) |
| -1 | Hi-hat pedal |

## Rhythm

Durations are in quarter-note beats. Use these values:

| duration | note |
|---|---|
| 4.0 | whole note |
| 3.0 | dotted half note |
| 2.0 | half note |
| 1.5 | dotted quarter note |
| 1.0 | quarter note |
| 0.5 | eighth note |

Beats per measure: 2/4 = 2, 3/4 = 3, 4/4 = 4, 5/4 = 5, 6/8 = 3, 9/8 = 4.5, 12/8 = 6, 2/2 = 4.

- **Every part must have the same total number of beats** (and a grand staff's `notes` and
  `lower_notes` too), a whole number of measures. Fill silences with rests.
- A note may run across a bar line; the app writes it as tied notes automatically.
- In 6/8, 9/8 and 12/8, a beat as felt is a dotted quarter (1.5); `tempo_bpm` still counts quarter
  notes (dotted-quarter beat at 60 = `tempo_bpm` 90).

## Keys

`"key"` is the number of sharps (positive) or flats (negative) of the song's key, as it sounds.
Transposing instruments get their own key signature automatically.

| key | major / minor |
|---|---|
| -7 | C♭ major / A♭ minor |
| -6 | G♭ major / E♭ minor |
| -5 | D♭ major / B♭ minor |
| -4 | A♭ major / F minor |
| -3 | E♭ major / C minor |
| -2 | B♭ major / G minor |
| -1 | F major / D minor |
| 0 | C major / A minor |
| 1 | G major / E minor |
| 2 | D major / B minor |
| 3 | A major / F♯ minor |
| 4 | E major / C♯ minor |
| 5 | B major / G♯ minor |
| 6 | F♯ major / D♯ minor |
| 7 | C♯ major / A♯ minor |

## What the app can't do, and what to do instead

Simplify, and add one sentence per change to `"ai_notes"`.

| In the song | Do this |
|---|---|
| Sixteenth notes, dotted eighths | Use eighths (merge pairs of sixteenths, or keep the first of each pair) |
| Triplets | Use the nearest eighths/quarters that keep the beat |
| Grace notes, trills, ornaments | Leave them out |
| Repeats, D.C., D.S., codas | Write the music out in full, in playing order |
| Pickup (anacrusis) | Start the first measure with rests so the pickup ends the first measure |
| Time signature or key changes | Use the main one for the whole song |
| Tempo changes | Use the main tempo |
| Double sharps or flats | Write the same pitch with a single sharp/flat or natural |
| Notes too high or low | Move them by an octave to fit steps -4 to 12 |
| Lyrics, dynamics, articulations | Leave them out (the app has none) |
| More than 64 measures | Use the best-known section (e.g. verse + chorus), within 64 measures |

## Arranging

Make a **full arrangement**, suited to the song's style, for example:
- **Melody:** an instrument that suits the song (e.g. Flute, Violin, Trumpet in B♭), or the piano's right hand.
- **Harmony:** `Piano (grand staff)` with chords (use `chord`); the right hand can carry the melody.
- **Bass:** `Bass Guitar`, `Cello` or `Tuba`, mostly the chord roots.
- **Drums:** `Drum Kit`, a simple steady pattern, if the style has drums.

Usually 2 to 5 parts. Keep every part the same length.

## Before you answer, check

1. The JSON is valid (double quotes, no trailing commas, no comments, no empty values) and has every
   key, with `"format": "music-staff"`, `"version": 6` and the time signature as text like `"4/4"`.
2. Every instrument name is copied exactly from the instrument table.
3. Every step comes from the right table: **treble-clef staves from the treble table, bass-clef staves
   (including every `lower_notes`) from the bass table**, drums from the drum table; all from
   -4 to 12. Transposing instruments use their *written* notes.
4. Every `alter` is the note's real pitch (-1, 0 or 1), including notes the key signature makes sharp or flat.
5. Every duration is from the rhythm table; rests have `"step": null`.
6. Every part (and each grand-staff hand) adds up to the same number of beats: whole measures.
7. `"ai_notes"` is one text string (not a list).
8. Each note is on its own line; the whole file is in one JSON code block.

## Example: "Hot Cross Buns"

Melody on piano (right hand) and Trumpet in B♭, chords in the piano's left hand, and drums. Notice the
trumpet's notes are written a whole step higher (sounding E is written F♯: step 1, alter 1), every
part totals 16 beats, and the drums use `chord` to play two drums at once.

```json
{
  "format": "music-staff",
  "version": 6,
  "tempo_bpm": 100,
  "key": 0,
  "time_signature": "4/4",
  "parts": [
    {
      "instrument": "Piano (grand staff)",
      "notes": [
        {"step": 0, "duration": 1.0, "alter": 0},
        {"step": -1, "duration": 1.0, "alter": 0},
        {"step": -2, "duration": 2.0, "alter": 0},
        {"step": 0, "duration": 1.0, "alter": 0},
        {"step": -1, "duration": 1.0, "alter": 0},
        {"step": -2, "duration": 2.0, "alter": 0},
        {"step": -2, "duration": 0.5, "alter": 0},
        {"step": -2, "duration": 0.5, "alter": 0},
        {"step": -2, "duration": 0.5, "alter": 0},
        {"step": -2, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": 0, "duration": 1.0, "alter": 0},
        {"step": -1, "duration": 1.0, "alter": 0},
        {"step": -2, "duration": 2.0, "alter": 0}
      ],
      "lower_notes": [
        {"step": 3, "duration": 4.0, "alter": 0, "chord": [[5, 0], [7, 0]]},
        {"step": 3, "duration": 4.0, "alter": 0, "chord": [[5, 0], [7, 0]]},
        {"step": 3, "duration": 2.0, "alter": 0, "chord": [[5, 0], [7, 0]]},
        {"step": 0, "duration": 2.0, "alter": 0, "chord": [[2, 0], [4, 0]]},
        {"step": 3, "duration": 4.0, "alter": 0, "chord": [[5, 0], [7, 0]]}
      ]
    },
    {
      "instrument": "Trumpet in B♭",
      "notes": [
        {"step": 1, "duration": 1.0, "alter": 1},
        {"step": 0, "duration": 1.0, "alter": 0},
        {"step": -1, "duration": 2.0, "alter": 0},
        {"step": 1, "duration": 1.0, "alter": 1},
        {"step": 0, "duration": 1.0, "alter": 0},
        {"step": -1, "duration": 2.0, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": -1, "duration": 0.5, "alter": 0},
        {"step": 0, "duration": 0.5, "alter": 0},
        {"step": 0, "duration": 0.5, "alter": 0},
        {"step": 0, "duration": 0.5, "alter": 0},
        {"step": 0, "duration": 0.5, "alter": 0},
        {"step": 1, "duration": 1.0, "alter": 1},
        {"step": 0, "duration": 1.0, "alter": 0},
        {"step": -1, "duration": 2.0, "alter": 0}
      ]
    },
    {
      "instrument": "Drum Kit",
      "notes": [
        {"step": 1, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 5, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 1, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 5, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 1, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 5, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 1, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0},
        {"step": 5, "duration": 1.0, "alter": 0, "chord": [[9, 0]]},
        {"step": 9, "duration": 1.0, "alter": 0}
      ]
    }
  ],
  "ai_notes": "Melody in the piano's right hand and the trumpet (written a whole step up); simple C and G chords in the left hand; a basic drum beat."
}
```

A reply in this form can be pasted straight into the app (File ▸ Paste Song) and saved as a
`.music.json` file.

## Song request

Translate this song (and follow any extra wishes written with it):

SONG REQUEST: 
