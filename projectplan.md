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
- Test sound: `python play_note.py` should play middle C. The "MIDI in devices" error lines are harmless.



## Milestones

Completed milestones are marked with ✅.

1. ✅ Set up the environment: install Python, a virtual environment, PySide6, FluidSynth, and a SoundFont. Play one note from a script.
2. ✅ Window with a single staff; click to place quarter notes; draw the notes.
3. ✅ Note durations palette, rests, delete; the data model (separate from drawing).
4. Playback with FluidSynth: Play/Pause/Stop, tempo, moving cursor.
5. Instrument tabs (add/remove), auto clef, mute/solo, multiple parts in sync.
6. Save/load JSON.
7. Undo/redo, dragging notes, pitch preview, scrolling as measures are added.



## Remember for Later (Don't Implement Yet)

Ideas we've agreed on but are deliberately leaving out for now. Revisit them after the milestones are done.

- **Ties across bar lines:** a note too long for what's left of its measure should be split at the bar line into two notes joined by a tie, e.g. a half note starting on beat 4 becomes two tied quarters. For now, the bar line goes after the note and that measure has too many beats. (Found in step 3c.)



## Risks / notes

- The Celeron N4120 is low-power. Playback timing must not depend on how long the GUI takes to redraw: schedule notes from a timer or sequencer, not from painting.
- The grand staff (piano), undo/redo, and dragging are the hardest features. They come last so a working app exists early.
