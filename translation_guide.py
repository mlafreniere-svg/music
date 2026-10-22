"""The AI translation guide: instructions for an AI chat to turn a song into
a Music Staff save file.

The guide is *generated* from the app's own data (instruments, limits, file
format), so it always matches what the app can do. The app copies it to the
clipboard (Help > Copy AI Translation Guide), and running this file writes
it to AI_TRANSLATION_GUIDE.md:

    python translation_guide.py
"""

import json
from pathlib import Path

from model import (
    DOTTED_HALF, DOTTED_QUARTER, DRUM_MAP, EIGHTH, HALF, HIGHEST_FILE_STEP, INSTRUMENT_GROUPS,
    KEY_NAMES, LOWEST_FILE_STEP, MAX_PARTS, QUARTER, TIME_SIGNATURES, WHOLE, Note, Score,
    find_instrument, measure_length, step_to_midi,
)
from storage import FILE_EXTENSION, FORMAT_NAME, FORMAT_VERSION, score_to_dict

GUIDE_FILE = Path(__file__).parent / "AI_TRANSLATION_GUIDE.md"
MAX_MEASURES = 64
LETTERS = "CDEFGAB"

DURATION_NAMES = {
    WHOLE: "whole note",
    DOTTED_HALF: "dotted half note",
    HALF: "half note",
    DOTTED_QUARTER: "dotted quarter note",
    QUARTER: "quarter note",
    EIGHTH: "eighth note",
}

# How each transposition is described to the AI (half steps -> words).
INTERVALS = {
    -2: "a whole step (2 half steps)",
    -7: "a perfect fifth (7 half steps)",
    -9: "a major sixth (9 half steps)",
    -12: "one octave (12 half steps)",
    -14: "an octave plus a whole step (14 half steps)",
}


def pitch_name(midi):
    """A natural (white-key) MIDI pitch as a name like "C4" (middle C)."""
    natural_semitones = [0, 2, 4, 5, 7, 9, 11]
    return LETTERS[natural_semitones.index(midi % 12)] + str(midi // 12 - 1)


def build_guide():
    """The whole guide, as one Markdown text."""
    sections = [
        intro(), file_format(), pitch_table(), instrument_table(), drum_table(),
        rhythm(), keys(), simplifying(), arranging(), self_check(), example(), request(),
    ]
    return "\n\n".join(sections) + "\n"


def intro():
    return f"""# Music Staff: AI translation guide

You are translating a song into a file for **Music Staff**, a small music-notation app. The person will
paste your reply into the app, which plays it. Follow this guide exactly: the app can only read files in
the format below, and only uses the features listed here.

**Your task:** arrange the requested song for the app, as a full arrangement (several instruments),
simplified to fit the app's limits. Write it as **one complete save file** in a single JSON code
block. Outside the code block, write nothing except, at most, one short sentence."""


def file_format():
    return f"""## The file format

The file is JSON with these keys:

| Key | Meaning |
|---|---|
| `"format"` | Exactly `"{FORMAT_NAME}"` (this exact text, not the app's name) |
| `"version"` | Exactly `{FORMAT_VERSION}` |
| `"tempo_bpm"` | Quarter-note beats per minute, 40 to 200 (whole number) |
| `"key"` | The key signature as a number (see "Keys") |
| `"time_signature"` | Text, one of: {", ".join(f'`"{t}/{b}"`' for t, b in TIME_SIGNATURES)} |
| `"parts"` | A list of instruments, 1 to {MAX_PARTS} |
| `"ai_notes"` | One text string for the person: what you simplified or changed |

Each part has:

| Key | Meaning |
|---|---|
| `"instrument"` | An exact name from the instrument table |
| `"notes"` | The part's notes, in order (for a grand staff: the right hand, treble clef) |
| `"lower_notes"` | Grand-staff instruments only: the left hand, bass clef |

Each note is `{{"step": S, "duration": D, "alter": A}}`, written **on one line**:
- `step`: where the note sits on the staff (see the pitch table). `null` for a rest.
- `duration`: its length in quarter-note beats (see "Rhythm").
- `alter`: the note's actual pitch relative to its letter: `-1` flat, `0` natural, `1` sharp.
  **Always write the real pitch**, even when the key signature has it: in G major, every F♯ has
  `"alter": 1`. (The key signature only changes how the app displays signs.) Rests use `0`.
- `chord` (optional): the other pitches played at the same time as `[step, alter]` pairs, e.g.
  `"chord": [[2, 0], [4, 0]]`. They share the note's duration. Never two pitches on the same step.

Notes follow one another: a part is a single line of notes and rests, one after another. Two
things at once in one part means a chord. Bar lines are added automatically from the time signature."""


def clef_users(clef):
    """Which staves use a clef, in words, from the instrument list."""
    names = [i.name for _, group in INSTRUMENT_GROUPS for i in group
             if i.clef == clef and not i.grand]
    if clef == "treble":
        return "the `notes` (right hand) of every grand-staff instrument, and " + ", ".join(names)
    return "the `lower_notes` (left hand) of every grand-staff instrument, and " + ", ".join(names)


def clef_table(clef):
    """Note name -> step for one clef, highest first."""
    line_names = {0: "bottom line", 2: "second line", 4: "middle line", 6: "fourth line", 8: "top line"}
    rows = []
    for step in range(HIGHEST_FILE_STEP, LOWEST_FILE_STEP - 1, -1):
        if step in line_names:
            where = line_names[step]
        elif 0 < step < 8:
            where = "space"
        elif step % 2 == 0:
            where = "ledger line"
        else:
            where = "space outside the staff"
        rows.append(f"| {pitch_name(step_to_midi(step, clef))} | {step} | {where} |")
    return "| note | step | position |\n|---|---|---|\n" + "\n".join(rows)


def pitch_table():
    g3_treble = next(s for s in range(-20, 20) if pitch_name(step_to_midi(s, "treble")) == "G3")
    g3_bass = next(s for s in range(-20, 20) if pitch_name(step_to_midi(s, "bass")) == "G3")
    return f"""## Pitch tables: note name -> step

Look up every step here; don't calculate it. **A step means a different note in treble and bass
clef, so use the table for the staff you are writing.** Using the treble table on a bass-clef staff
gives wrong notes: G3 is step {g3_treble} in treble clef but step {g3_bass} in bass clef.

Middle C is C4. A sharp or flat uses the natural note's step plus `alter` (F♯4 in treble clef =
step 1, alter 1). Steps must stay from {LOWEST_FILE_STEP} to {HIGHEST_FILE_STEP}; if a note is
outside the table, move it up or down an octave.

### Treble-clef staves
Used by {clef_users("treble")}.
(Transposing instruments: look up the *written* note.)

{clef_table("treble")}

### Bass-clef staves
Used by {clef_users("bass")}.
(Transposing instruments: look up the *written* note.)

{clef_table("bass")}"""


def instrument_table():
    rows = []
    for heading, instruments in INSTRUMENT_GROUPS:
        for instrument in instruments:
            if instrument.is_drums:
                staff, written = "drum staff", "steps are drums, not pitches (see the drum table)"
            elif instrument.grand:
                staff, written = "grand staff (`notes` treble, `lower_notes` bass)", "as it sounds"
            elif instrument.transpose:
                # An example pitch in the instrument's own range: C4 for treble, C2 for bass.
                sounding = 60 if instrument.clef == "treble" else 36
                written_pitch = pitch_name(sounding - instrument.transpose)
                staff = f"{instrument.clef} clef"
                written = (f"**{INTERVALS[instrument.transpose]} higher than it sounds** "
                           f"(sounding {pitch_name(sounding)} is written {written_pitch})")
            else:
                staff, written = f"{instrument.clef} clef", "as it sounds"
            rows.append(f"| `{instrument.name}` | {heading} | {staff} | {written} |")
    return f"""## Instruments

Use these exact names. At most {MAX_PARTS} parts.

**Transposing instruments are written at a different pitch than they sound.** Choose the sounding
notes, then write each one higher by the amount shown (adding sharps or flats as needed), and look up
the *written* note's step. Everything else is written as it sounds.

| Name | Group | Staff | How to write it |
|---|---|---|---|
""" + "\n".join(rows)


def drum_table():
    rows = [f"| {step} | {drum.name} |" for step, drum in sorted(DRUM_MAP.items(), reverse=True)]
    return """## Drum table (for "Drum Kit")

On a drum staff each step is a drum. Use only these steps, `alter` 0. Use `chord` to hit drums
together (e.g. kick + hi-hat: `{"step": 1, "duration": 1.0, "alter": 0, "chord": [[9, 0]]}`).

| step | drum |
|---|---|
""" + "\n".join(rows)


def rhythm():
    durations = "\n".join(f"| {value} | {name} |" for value, name in DURATION_NAMES.items())
    measures = ", ".join(f"{t}/{b} = {measure_length((t, b)):g}" for t, b in TIME_SIGNATURES)
    return f"""## Rhythm

Durations are in quarter-note beats. Use these values:

| duration | note |
|---|---|
{durations}

Beats per measure: {measures}.

- **Every part must have the same total number of beats** (and a grand staff's `notes` and
  `lower_notes` too), a whole number of measures. Fill silences with rests.
- A note may run across a bar line; the app writes it as tied notes automatically.
- In 6/8, 9/8 and 12/8, a beat as felt is a dotted quarter (1.5); `tempo_bpm` still counts quarter
  notes (dotted-quarter beat at 60 = `tempo_bpm` 90)."""


def keys():
    rows = "\n".join(f"| {key} | {major} / {minor} |" for key, (major, minor) in sorted(KEY_NAMES.items()))
    return f"""## Keys

`"key"` is the number of sharps (positive) or flats (negative) of the song's key, as it sounds.
Transposing instruments get their own key signature automatically.

| key | major / minor |
|---|---|
{rows}"""


def simplifying():
    return f"""## What the app can't do, and what to do instead

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
| Notes too high or low | Move them by an octave to fit steps {LOWEST_FILE_STEP} to {HIGHEST_FILE_STEP} |
| Lyrics, dynamics, articulations | Leave them out (the app has none) |
| More than {MAX_MEASURES} measures | Use the best-known section (e.g. verse + chorus), within {MAX_MEASURES} measures |"""


def arranging():
    return """## Arranging

Make a **full arrangement**, suited to the song's style, for example:
- **Melody:** an instrument that suits the song (e.g. Flute, Violin, Trumpet in B♭), or the piano's right hand.
- **Harmony:** `Piano (grand staff)` with chords (use `chord`); the right hand can carry the melody.
- **Bass:** `Bass Guitar`, `Cello` or `Tuba`, mostly the chord roots.
- **Drums:** `Drum Kit`, a simple steady pattern, if the style has drums.

Usually 2 to 5 parts. Keep every part the same length."""


def self_check():
    return f"""## Before you answer, check

1. The JSON is valid (double quotes, no trailing commas, no comments, no empty values) and has every
   key, with `"format": "{FORMAT_NAME}"`, `"version": {FORMAT_VERSION}` and the time signature as text like `"4/4"`.
2. Every instrument name is copied exactly from the instrument table.
3. Every step comes from the right table: **treble-clef staves from the treble table, bass-clef staves
   (including every `lower_notes`) from the bass table**, drums from the drum table; all from
   {LOWEST_FILE_STEP} to {HIGHEST_FILE_STEP}. Transposing instruments use their *written* notes.
4. Every `alter` is the note's real pitch (-1, 0 or 1), including notes the key signature makes sharp or flat.
5. Every duration is from the rhythm table; rests have `"step": null`.
6. Every part (and each grand-staff hand) adds up to the same number of beats: whole measures.
7. `"ai_notes"` is one text string (not a list).
8. Each note is on its own line; the whole file is in one JSON code block."""


def example_score():
    """Hot Cross Buns as a real Score: the guide's example, built from app data so it always loads."""
    score = Score(tempo_bpm=100, key=0, time_signature=(4, 4))
    piano = score.add_part(find_instrument("Piano (grand staff)"))
    three_notes = [Note(0), Note(-1), Note(-2, HALF)]                     # E4 D4 C4
    piano.notes = (three_notes + three_notes
                   + [Note(-2, EIGHTH)] * 4 + [Note(-1, EIGHTH)] * 4      # C C C C D D D D
                   + three_notes)
    c_chord = Note(3, WHOLE, chord=[(5, 0), (7, 0)])                      # C3 E3 G3
    g_chord = Note(0, WHOLE, chord=[(2, 0), (4, 0)])                      # G2 B2 D3
    piano.lower.notes = [c_chord, c_chord, Note(3, HALF, chord=[(5, 0), (7, 0)]),
                         Note(0, HALF, chord=[(2, 0), (4, 0)]), c_chord]
    trumpet = score.add_part(find_instrument("Trumpet in B♭"))
    # The melody, written a whole step up: sounding E D C -> written F# E D.
    written = [Note(1, alter=1), Note(0), Note(-1, HALF)]
    trumpet.notes = (written + written
                     + [Note(-1, EIGHTH)] * 4 + [Note(0, EIGHTH)] * 4
                     + written)
    drums = score.add_part(find_instrument("Drum Kit"))
    bar = [Note(1, chord=[(9, 0)]), Note(9), Note(5, chord=[(9, 0)]), Note(9)]  # kick, hat, snare, hat
    drums.notes = bar * 4
    return score


def file_text(data):
    """A save file as text, with each note on one line (short, and easy to check).

    json.dumps(data, indent=2) would put every key of every note on its own
    line, making a long song very long, so we lay it out by hand.
    """
    def value(v):
        return json.dumps(v, ensure_ascii=False)  # ensure_ascii=False keeps ♭ as ♭

    def note_list(notes):
        lines = ["        " + value(note) for note in notes]
        return "[\n" + ",\n".join(lines) + "\n      ]"

    part_texts = []
    for part in data["parts"]:
        fields = [f'      "instrument": {value(part["instrument"])}',
                  f'      "notes": {note_list(part["notes"])}']
        if "lower_notes" in part:
            fields.append(f'      "lower_notes": {note_list(part["lower_notes"])}')
        part_texts.append("    {\n" + ",\n".join(fields) + "\n    }")

    lines = []
    for key, v in data.items():  # keeps the keys in their order
        if key == "parts":
            lines.append('  "parts": [\n' + ",\n".join(part_texts) + "\n  ]")
        else:
            lines.append(f'  "{key}": {value(v)}')
    return "{\n" + ",\n".join(lines) + "\n}"


def example_data():
    data = score_to_dict(example_score())
    data["ai_notes"] = ("Melody in the piano's right hand and the trumpet (written a whole step up); "
                        "simple C and G chords in the left hand; a basic drum beat.")
    return data


def example():
    return f"""## Example: "Hot Cross Buns"

Melody on piano (right hand) and Trumpet in B♭, chords in the piano's left hand, and drums. Notice the
trumpet's notes are written a whole step higher (sounding E is written F♯: step 1, alter 1), every
part totals 16 beats, and the drums use `chord` to play two drums at once.

```json
{file_text(example_data())}
```

A reply in this form can be pasted straight into the app (File ▸ Paste Song) and saved as a
`{FILE_EXTENSION}` file."""


def request():
    return """## Song request

Translate this song (and follow any extra wishes written with it):

SONG REQUEST: """


if __name__ == "__main__":
    # Running this file directly writes the guide to AI_TRANSLATION_GUIDE.md.
    GUIDE_FILE.write_text(build_guide(), encoding="utf-8")
    print(f"Wrote {GUIDE_FILE}")
