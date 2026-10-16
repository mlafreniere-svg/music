"""Playback: turns a Part into sound through FluidSynth.

The Player is a QObject so it can use a Qt timer and send signals (for
example "now playing note 3") that the window can listen to.
"""

import time
from pathlib import Path

import fluidsynth
from PySide6.QtCore import QObject, Qt, QTimer, Signal

SOUNDFONT = Path(__file__).parent / "soundfonts" / "GeneralUser-GS.sf2"

CHANNEL = 0     # MIDI channel; milestone 5 gives each instrument its own
VELOCITY = 100  # how hard each key is struck, 0-127
PIANO = 0       # General MIDI program number for Acoustic Grand Piano


class Player(QObject):
    """Plays the notes of a part, one after another, at a given tempo."""

    # Signals this object can send. Other code connects to them, like the
    # toolbar buttons' signals. Signal(int) means it sends one whole number.
    note_started = Signal(int)  # the index of the note that just started
    finished = Signal()         # the part reached its end

    def __init__(self):
        super().__init__()
        self.tempo_bpm = 100  # beats (quarter notes) per minute

        self.synth = fluidsynth.Synth()
        # Open only the audio output. (Synth.start() would also open a MIDI
        # *input* for a hardware keyboard, which prints errors when there
        # isn't one plugged in.)
        self.synth.setting("audio.driver", "dsound")
        self.synth.audio_driver = fluidsynth.new_fluid_audio_driver(
            self.synth.settings, self.synth.synth
        )
        soundfont_id = self.synth.sfload(str(SOUNDFONT))
        self.synth.program_select(CHANNEL, soundfont_id, 0, PIANO)

        # A single-shot timer fires once, after the delay we give it.
        # PreciseTimer asks Windows for millisecond accuracy.
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.play_next_note)

        self.notes = []            # what's being played
        self.clef = "treble"
        self.index = 0             # which note plays next
        self.sounding_pitch = None # the MIDI pitch currently held down, if any
        self.next_start_time = 0.0 # when the next note should begin (seconds)

    def play(self, part, clef="treble"):
        """Start playing a part from the beginning."""
        self.stop()
        # Copy the list, so editing the staff during playback can't change
        # what's being played halfway through.
        self.notes = list(part.notes)
        self.clef = clef
        self.index = 0
        # perf_counter() is a high-precision clock, in seconds. Only the
        # differences between its readings matter.
        self.next_start_time = time.perf_counter()
        self.play_next_note()

    def stop(self):
        """Stop playing and silence the current note."""
        self.timer.stop()
        self.release_note()

    def is_playing(self):
        return self.timer.isActive()

    def play_next_note(self):
        """Play one note, then set the timer for the one after it.

        Called by play() for the first note, then by the timer for each
        following note: the timer "chains" the notes together.
        """
        self.release_note()  # let go of the previous note
        if self.index >= len(self.notes):
            self.finished.emit()  # emit = send the signal
            return

        note = self.notes[self.index]
        pitch = note.midi_pitch(self.clef)
        if pitch is not None:  # rests make no sound
            self.synth.noteon(CHANNEL, pitch, VELOCITY)
            self.sounding_pitch = pitch
        self.note_started.emit(self.index)

        # Drift-free scheduling: work out when the next note *should* start,
        # then wait only for whatever time is left until then. If this note
        # started a few milliseconds late, the next wait is shorter, so small
        # delays never add up.
        seconds_per_beat = 60 / self.tempo_bpm
        self.next_start_time += note.duration * seconds_per_beat
        self.index += 1
        wait_seconds = self.next_start_time - time.perf_counter()
        self.timer.start(max(0, round(wait_seconds * 1000)))  # in milliseconds

    def release_note(self):
        """Stop the note that is sounding, if there is one."""
        if self.sounding_pitch is not None:
            self.synth.noteoff(CHANNEL, self.sounding_pitch)
            self.sounding_pitch = None

    def close(self):
        """Shut the synthesizer down. Call once, when the app exits."""
        self.stop()
        self.synth.delete()
