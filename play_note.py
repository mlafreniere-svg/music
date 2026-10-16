"""Milestone 1 check: play one note through FluidSynth.

If you hear a piano note for about one second, Python, pyfluidsynth,
FluidSynth, and the SoundFont are all working together.
"""

import time
from pathlib import Path

import fluidsynth  # the pyfluidsynth package; it loads libfluidsynth-3.dll

# Build the SoundFont's path relative to this file, so the script works
# no matter which folder you run it from.
SOUNDFONT = Path(__file__).parent / "soundfonts" / "GeneralUser-GS.sf2"

# MIDI describes notes as numbers: 60 is middle C, and each step is a half step.
MIDDLE_C = 60
VELOCITY = 100  # how hard the key is struck, 0-127 (louder = higher)
CHANNEL = 0     # MIDI has 16 channels; each one can play a different instrument
GAIN = 0.6      # master volume, 0-10 (pyfluidsynth's default, 0.2, is too quiet)

synth = fluidsynth.Synth(gain=GAIN)
synth.start(driver="dsound")  # DirectSound: the standard Windows audio output

soundfont_id = synth.sfload(str(SOUNDFONT))
# Program 0 is "Acoustic Grand Piano" in the General MIDI instrument list.
synth.program_select(CHANNEL, soundfont_id, 0, 0)

synth.noteon(CHANNEL, MIDDLE_C, VELOCITY)   # press the key
time.sleep(1.0)
synth.noteoff(CHANNEL, MIDDLE_C)            # release the key
time.sleep(1.0)                             # let the sound fade out

synth.delete()  # shut down the synthesizer cleanly
print("Done! Did you hear middle C?")
