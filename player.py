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
GAIN = 0.6      # master volume, 0-10; above ~1 notes played together can distort


# The player is always in exactly one of these states.
STOPPED = "stopped"
PLAYING = "playing"
PAUSED = "paused"


class Player(QObject):
    """Plays the notes of a part, one after another, at a given tempo."""

    # Signals this object can send. Other code connects to them, like the
    # toolbar buttons' signals. Signal(int) means it sends one whole number.
    note_started = Signal(int)  # the index of the note that just started
    finished = Signal()         # the part reached its end
    state_changed = Signal(str) # the new state: STOPPED, PLAYING, or PAUSED

    def __init__(self):
        super().__init__()
        self.tempo_bpm = 100  # beats (quarter notes) per minute

        self.synth = fluidsynth.Synth(gain=GAIN)  # pyfluidsynth's default, 0.2, is too quiet
        # Open only the audio output. (Synth.start() would also open a MIDI
        # *input* for a hardware keyboard, which prints errors when there
        # isn't one plugged in.)
        self.synth.setting("audio.driver", "dsound")
        self.synth.audio_driver = fluidsynth.new_fluid_audio_driver(
            self.synth.settings, self.synth.synth
        )
        self.soundfont_id = self.synth.sfload(str(SOUNDFONT))
        self.synth.program_select(CHANNEL, self.soundfont_id, 0, PIANO)

        # A single-shot timer fires once, after the delay we give it.
        # PreciseTimer asks Windows for millisecond accuracy.
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.play_next_note)

        self.state = STOPPED
        self.notes = []            # what's being played
        self.clef = "treble"
        self.index = 0             # which note plays next
        self.sounding_pitch = None # the MIDI pitch currently held down, if any
        self.next_start_time = 0.0 # when the next note should begin (seconds)
        self.paused_pitch = None   # the note that was sounding when we paused
        self.time_left = 0.0       # seconds left on that note when we paused

    def set_state(self, state):
        """Change state and tell anyone listening (the window's buttons)."""
        self.state = state
        self.state_changed.emit(state)

    def play(self, part):
        """Resume if paused; otherwise start the part from the beginning."""
        if self.state == PAUSED:
            self.resume()
            return
        self.stop()
        # Copy the list, so editing the staff during playback can't change
        # what's being played halfway through.
        self.notes = list(part.notes)
        self.clef = part.clef  # the same staff step is a different pitch in each clef
        # Switch the channel to this part's instrument sound ("program").
        self.synth.program_select(CHANNEL, self.soundfont_id, 0, part.instrument.program)
        self.index = 0
        # perf_counter() is a high-precision clock, in seconds. Only the
        # differences between its readings matter.
        self.next_start_time = time.perf_counter()
        self.set_state(PLAYING)
        self.play_next_note()

    def pause(self):
        """Freeze playback where it is, remembering how far into the note we were."""
        if self.state != PLAYING:
            return
        self.timer.stop()
        self.time_left = max(0.0, self.next_start_time - time.perf_counter())
        self.paused_pitch = self.sounding_pitch
        self.release_note()
        self.set_state(PAUSED)

    def resume(self):
        """Continue after a pause: finish the paused note, then carry on."""
        if self.state != PAUSED:
            return
        # Re-sound the note that was cut off, for the time it had left.
        if self.paused_pitch is not None:
            self.synth.noteon(CHANNEL, self.paused_pitch, VELOCITY)
            self.sounding_pitch = self.paused_pitch
        # Shift the schedule: the next note is due time_left seconds from *now*.
        self.next_start_time = time.perf_counter() + self.time_left
        self.timer.start(round(self.time_left * 1000))
        self.set_state(PLAYING)

    def stop(self):
        """Stop playing, silence the current note, and go back to the start."""
        self.timer.stop()
        self.release_note()
        self.index = 0
        if self.state != STOPPED:
            self.set_state(STOPPED)

    def play_next_note(self):
        """Play one note, then set the timer for the one after it.

        Called by play() for the first note, then by the timer for each
        following note: the timer "chains" the notes together.
        """
        self.release_note()  # let go of the previous note
        if self.index >= len(self.notes):
            self.stop()
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
