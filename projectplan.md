# Goal

A working music writing tool, that can be played by entering notes on a musical staff.



## Assumptions

Run locally on Windows machine in Python. Single user. 

Device name	LAPTOP-LNO1DLEP

Processor	Intel(R) Celeron(R) N4120 CPU @ 1.10GHz   1.10 GHz

Installed RAM	16.0 GB (15.8 GB usable)

Device ID	BEC003ED-68AA-4518-9195-A19E7E5C7984

Product ID	00356-07485-69537-AAOEM

System type	64-bit operating system, x64-based processor

Pen and touch	No pen or touch input is available for this display

### Deliverables

Tabs for each instrument with a blank staff that can be edited to add notes. Play and pause buttons. When play button is hit, chosen instrument will play music from the staff. Pause pauses the music.



## Decisions (from requirements interview, 2026-10-16)

- **Purpose:** Learning project. Developer is new to Python. Built step-by-step together in small milestones, with explanations.
- **Stack:** Python 3.12, PySide6 (Qt) GUI, FluidSynth + General MIDI SoundFont (.sf2) for sound.
- **Instruments:** Tabs can be added and removed with a "+" button; the instrument comes from a General MIDI list, and repeats are allowed.
- **Clef:** Set automatically by instrument (treble, bass, or grand staff for piano).
- **Notation (minimal):** Single-note line; whole, half, quarter, and eighth notes; rests. Fixed key (C) and 4/4 time.
- **Length/tempo:** Measures are added as needed and the staff scrolls horizontally. One BPM slider for the whole piece.
- **Input:** Choose a duration from a palette, then click the staff; vertical position sets the pitch. No touch or pen input.
- **Editing:** Delete a note (right-click/Delete), undo/redo (Ctrl+Z/Ctrl+Y), hear the pitch when a note is placed, drag notes to move them.
- **Playback:** All tabs play in sync, with per-tab Mute/Solo. Play / Pause (resume from same spot) / Stop (back to start). A cursor shows the current position.
- **Persistence:** Save/load the project as JSON. MIDI export is out of scope for now.



## Setup

- Python 3.12.10, installed with winget.
- FluidSynth v2.6.1 in `C:\Users\mason\tools\fluidsynth\fluidsynth-v2.6.1-win10-x64-cpp11\` (its `bin` folder is on the user PATH).
- SoundFont: GeneralUser GS, saved at `soundfonts\GeneralUser-GS.sf2` (not in git; download from https://github.com/mrbumpy409/GeneralUser-GS).
- Python packages: `pip install -r requirements.txt` inside the `.venv` virtual environment.
- Each session: `cd C:\Users\mason\src\music`, then `.venv\Scripts\Activate.ps1`.
- Saved scores: `saved_music\` in the project folder (`*.music.json`). The Open/Save dialogs start there.
- Test sound: `python play_note.py` should play middle C. The "MIDI in devices" error lines are harmless.



## Milestones

Completed milestones are marked with ✅.

1. ✅ Set up the environment: install Python, a virtual environment, PySide6, FluidSynth, and a SoundFont. Play one note from a script.
2. ✅ Window with a single staff; click to place quarter notes; draw the notes.
3. ✅ Note durations palette, rests, delete; the data model (separate from drawing).
4. ✅ Playback with FluidSynth: Play/Pause/Stop, tempo, moving cursor.
5. ✅ Instrument tabs (add/remove), auto clef, mute/solo, multiple parts in sync.
6. ✅ Save/load JSON.
7. ✅ Undo/redo, dragging notes, pitch preview, scrolling as measures are added.



## Remember for Later (Don't Implement Yet)

Ideas we've agreed on but are deliberately leaving out for now. Revisit them after the milestones are done.

- **Show and choose the instrument:** playback is Acoustic Grand Piano, hard-coded in `player.py` (`PIANO = 0`, General MIDI program 0), and the app never says so. When milestone 5 adds instruments, make the current instrument visible on each tab and let the user choose it. (Raised during step 4c.) ✅ *Done. Milestone 5 labeled the tabs and let you pick the instrument when adding one; now right-clicking a tab changes its instrument (undoable). On a clef change, notes keep their letter names and move by whole octaves to fit the new staff.*
- **Grand staff for piano:** piano gets two joined staves (treble + bass) in one part. Deferred in milestone 5: piano uses treble clef, and a separate "Piano (bass)" tab covers low notes. (Decided at the start of milestone 5.) ✅ *Done: "Keyboards (grand staff)" instruments (Piano, Organ, Harp, Marimba); new scores start with one. A part's `lower` staff holds the left hand, played together with the right. Staves share beat-based columns so notes and bar lines line up; brace and joining line drawn by `GrandStaffWidget`. Grand staff tabs switch only between keyboards. File format version 3 (older files still open).*
- **Transposing instruments:** trumpet, clarinet, saxophone, guitar, and double bass are written at a different pitch than they sound. Milestone 5's instrument list leaves them out; adding them means each instrument needs a "transposition" in half steps. (Decided at the start of milestone 5.) ✅ *Done: guitars, bass guitar, double bass, B♭ trumpet and clarinet, horn in F, alto and tenor sax. Parts show written pitch with their own key signature; playback uses sounding pitch; switching instruments keeps the sound. Also a Drum Kit: percussion clef, each line/space is a drum (kick, snare, hi-hat, toms, cymbals with × heads), clicks snap to the nearest drum, the status bar names the drum under the mouse.*
- **Time signature changes partway through a piece:** a new meter at any measure (e.g. 4/4 then 3/4). Measures, saving and drawing would all need per-measure meters. (Decided when adding time signatures.)
- **Sixteenth notes and dotted eighths:** a dotted eighth (¾ beat) leaves gaps only sixteenths can fill, so dots are limited to half and quarter notes for now. (Decided when adding time signatures.)
- **Full score PDF:** all instruments stacked on every printed line with measures aligned between them (like a conductor's score). The PDF currently prints each instrument in turn. (Decided when adding PDF export.)
- **Concert pitch toggle:** a switch to show every part at sounding pitch instead of written pitch (as notation programs offer). (Decided while adding transposing instruments.) ✅ *Done: "Concert Pitch" in the Playback toolbar and View menu (a view setting: not saved, not undoable). Octave transposers (guitars, basses) look the same either way. Editing works in both views; edits are stored at written pitch.*
- **Ties across bar lines:** a note too long for what's left of its measure should be split at the bar line into two notes joined by a tie, e.g. a half note starting on beat 4 becomes two tied quarters. For now, the bar line goes after the note and that measure has too many beats. (Found in step 3c.) ✅ *Done: notes are stored whole (they sound as one note); `Part.pieces()` splits them at bar lines into tied note values for drawing. Clicking, dragging, or deleting any piece acts on the whole note.*
- **Sharps, flats, and key signatures:** "minimal notation" left them out, so only natural notes (the piano's white keys) can be written. Needs accidentals on notes (♯ ♭ ♮), drawing them, pitch math that includes them, and saving them; key signatures come after. Transposing instruments depend on this. (Noted after milestone 7.) ✅ *Done: notes store their real pitch (`alter`); signs follow the standard measure rule; toolbar Key/♮/♯/♭ for new notes; point + `+`/`-` to change a note; Key drop-down with all 15 keys; file format version 2 (version 1 files still open).*
- **MIDI export:** save a standard `.mid` file that MuseScore, a DAW, or any music program can open. Was "out of scope for now" in the original plan; small now that save/load exists. Exported files are songs, so they stay out of git like `saved_music`. (Noted after milestone 7.) ✅ *Done: File ▸ Export MIDI (Ctrl+E). Written by hand in `midi_export.py` (format 1: a conductor track with tempo/time/key, one track per part at sounding pitch, drums on channel 10). `*.mid` is git-ignored.*



## After the plan

Features added after the milestones and the Remember for Later list were finished.

- ✅ **Time signatures:** 2/4, 3/4, 4/4, 5/4, 6/8, 9/8, 12/8, 2/2, one per piece (Score toolbar; undoable; drawn after the key; saved as file format version 4; written to MIDI). Changing it re-bars the same notes.
- ✅ **Dotted notes:** Dot (.) for half and quarter notes; ties use dotted values where they fit (3 beats = one dotted half).
- ✅ **Chords:** Shift+click adds or removes a pitch on a note; heads share a stem, seconds sit on opposite sides, signs stagger left, columns widen to fit. Dragging and + / − act on one head. File format version 5; playback, MIDI and transposition use every head.
- ✅ **Print to PDF:** File ▸ Print to PDF (Ctrl+P): US Letter, each instrument in turn, lines broken at bar lines with the clef and key repeated (time signature on the first line only). Written pitch. `*.pdf` is git-ignored.



## Risks / notes

- The Celeron N4120 is low-power. Playback timing must not depend on how long the GUI takes to redraw: schedule notes from a timer or sequencer, not from painting.
- The grand staff (piano), undo/redo, and dragging are the hardest features. They come last so a working app exists early.
