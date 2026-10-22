# Music Staff

A Windows desktop app for writing music: click notes onto a staff, and it plays them back with real
instrument sounds. Written in Python (PySide6 for the window, FluidSynth for sound) as a learning project.

https://github.com/user-attachments/assets/f4a277b2-fd4f-487e-ae2c-a9f624aba14f

## Features

- Click notes onto a staff, from whole notes to eighths, plus dotted notes, rests, sharps and flats, and chords
- One tab for each instrument, all playing together, with Mute and Solo for each tab
- Piano and other keyboards on a grand staff (two staves); drums; transposing instruments shown at
  written pitch, with a Concert Pitch view
- Key and time signatures, ties across bar lines, undo and redo, and dragging notes
- Save and open songs, export MIDI, and print to PDF
- **Paste Song from AI:** give an AI chat the app's translation guide and a song name, then paste
  its reply in to get a full arrangement

## Running it

1. Install Python 3.12 and [FluidSynth](https://github.com/FluidSynth/fluidsynth/releases) (its `bin`
   folder on your PATH).
2. Download the [GeneralUser GS](https://github.com/mrbumpy409/GeneralUser-GS) SoundFont and save it as
   `soundfonts\GeneralUser-GS.sf2`.
3. In PowerShell, from this folder:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py
   ```

How to use the app is in [USER_GUIDE.md](USER_GUIDE.md), which the app also shows under Help (F1).
How it was built, milestone by milestone, is in [projectplan.md](projectplan.md).
