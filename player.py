"""Playback: turns a Score into sound through FluidSynth.

The Player is a QObject so it can use a Qt timer and send signals (for
example "part 1 just started its note 3") that the window can listen to.
"""

import time
from pathlib import Path

import fluidsynth
from PySide6.QtCore import QObject, Qt, QTimer, Signal

SOUNDFONT = Path(__file__).parent / "soundfonts" / "GeneralUser-GS.sf2"

VELOCITY = 100  # how hard each key is struck, 0-127
GAIN = 0.6      # master volume, 0-10; above ~1 notes played together can distort

# MIDI has 16 channels, 0-15. Each part gets its own channel so it can have
# its own instrument sound. Channel 9 is reserved for drums in General MIDI,
# and channel 15 is kept for previews (hearing a note as you place it),
# leaving 14 channels: at most 14 parts.
DRUM_CHANNEL = 9
PREVIEW_CHANNEL = 15
CHANNELS = [c for c in range(16) if c not in (DRUM_CHANNEL, PREVIEW_CHANNEL)]
MAX_PARTS = len(CHANNELS)

PREVIEW_SECONDS = 0.4  # how long a preview note sounds
PREVIEW_VELOCITY = 90  # a little softer than playback


# The player is always in exactly one of these states.
STOPPED = "stopped"
PLAYING = "playing"
PAUSED = "paused"


class Player(QObject):
    """Plays all the parts of a score together, at a given tempo."""

    # Signals this object can send. Other code connects to them, like the
    # toolbar buttons' signals. Signal(int, int) sends two whole numbers.
    note_started = Signal(int, int)  # (part index, note index) of a note that just started
    finished = Signal()              # the score reached its end
    state_changed = Signal(str)      # the new state: STOPPED, PLAYING, or PAUSED

    def __init__(self):
        super().__init__()

        self.synth = fluidsynth.Synth(gain=GAIN)  # pyfluidsynth's default, 0.2, is too quiet
        # Open only the audio output. (Synth.start() would also open a MIDI
        # *input* for a hardware keyboard, which prints errors when there
        # isn't one plugged in.)
        self.synth.setting("audio.driver", "dsound")
        self.synth.audio_driver = fluidsynth.new_fluid_audio_driver(
            self.synth.settings, self.synth.synth
        )
        self.soundfont_id = self.synth.sfload(str(SOUNDFONT))

        # A single-shot timer fires once, after the delay we give it.
        # PreciseTimer asks Windows for millisecond accuracy.
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.play_next_events)

        # A second timer just for ending preview notes.
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.end_preview)
        self.preview_pitch = None  # the preview note that's sounding, if any

        self.state = STOPPED
        self.score = None          # the score being played (for Mute/Solo)
        self.events = []           # the score's timeline (see Score.timeline)
        self.event_index = 0       # the next event to handle
        self.sounding = set()      # (channel, pitch) pairs currently held down
        self.next_start_time = 0.0 # when the next event is due (seconds)
        self.paused_sounding = set() # what was sounding when we paused
        self.time_left = 0.0       # seconds until the next event, when we paused

    def set_state(self, state):
        """Change state and tell anyone listening (the window's buttons)."""
        self.state = state
        self.state_changed.emit(state)

    def play(self, score):
        """Resume if paused; otherwise start the whole score from the beginning."""
        if self.state == PAUSED:
            self.resume()
            return
        self.stop()
        # Keep the score itself (not a copy) so Mute/Solo changes made during
        # playback are seen right away.
        self.score = score
        # The timeline is a new list built from the score right now, so
        # editing the staff during playback can't change what's being played.
        self.events = score.timeline()
        self.event_index = 0
        # Give each part's channel that part's instrument sound ("program").
        for part_index, part in enumerate(score.parts):
            channel = CHANNELS[part_index]
            self.synth.program_select(channel, self.soundfont_id, 0, part.instrument.program)
        if not self.events:
            return  # nothing written yet
        # perf_counter() is a high-precision clock, in seconds. Only the
        # differences between its readings matter.
        self.next_start_time = time.perf_counter()
        self.set_state(PLAYING)
        self.play_next_events()

    def pause(self):
        """Freeze playback where it is, remembering what was sounding."""
        if self.state != PLAYING:
            return
        self.timer.stop()
        self.time_left = max(0.0, self.next_start_time - time.perf_counter())
        self.paused_sounding = set(self.sounding)  # a copy, since release_all empties it
        self.release_all()
        self.set_state(PAUSED)

    def resume(self):
        """Continue after a pause: re-sound the held notes, then carry on."""
        if self.state != PAUSED:
            return
        for channel, pitch in self.paused_sounding:
            if self.is_audible(CHANNELS.index(channel)):  # it may have been muted meanwhile
                self.synth.noteon(channel, pitch, VELOCITY)
                self.sounding.add((channel, pitch))
        # Shift the schedule: the next event is due time_left seconds from *now*.
        self.next_start_time = time.perf_counter() + self.time_left
        self.timer.start(round(self.time_left * 1000))
        self.set_state(PLAYING)

    def stop(self):
        """Stop playing, silence everything, and go back to the start."""
        self.timer.stop()
        self.release_all()
        self.event_index = 0
        if self.state != STOPPED:
            self.set_state(STOPPED)

    def play_next_events(self):
        """Handle every event due at the current beat, then set the timer.

        Called by play() for the first beat, then by the timer: the timer
        "chains" the beats together, just as it chained notes before.
        """
        beat = self.events[self.event_index].beat
        # Handle all the events at this beat. Endings come first in the
        # timeline, so a note is released before a new one starts.
        while self.event_index < len(self.events) and self.events[self.event_index].beat == beat:
            event = self.events[self.event_index]
            channel = CHANNELS[event.part_index]
            if event.starts:
                # Rests make no sound, and neither do muted parts. The cursor
                # still moves either way (note_started below).
                if event.pitch is not None and self.is_audible(event.part_index):
                    self.synth.noteon(channel, event.pitch, VELOCITY)
                    self.sounding.add((channel, event.pitch))
                self.note_started.emit(event.part_index, event.note_index)
            elif event.pitch is not None:
                self.synth.noteoff(channel, event.pitch)
                self.sounding.discard((channel, event.pitch))  # discard: remove if present
            self.event_index += 1

        if self.event_index >= len(self.events):
            self.stop()
            self.finished.emit()  # emit = send the signal
            return

        # Drift-free scheduling: work out when the next event *should* happen,
        # then wait only for whatever time is left until then. If this beat
        # was handled a few milliseconds late, the next wait is shorter, so
        # small delays never add up. Counting in beats (not seconds) means a
        # tempo change applies from the next event on.
        seconds_per_beat = 60 / self.score.tempo_bpm  # read every time, so slider changes apply
        next_beat = self.events[self.event_index].beat
        self.next_start_time += (next_beat - beat) * seconds_per_beat
        wait_seconds = self.next_start_time - time.perf_counter()
        self.timer.start(max(0, round(wait_seconds * 1000)))  # in milliseconds

    def is_audible(self, part_index):
        """Should this part be heard right now (Mute/Solo)?"""
        if self.score is None or part_index >= len(self.score.parts):
            return False
        return self.score.is_audible(part_index)

    def apply_mutes(self):
        """Silence held notes of parts that were just muted (or un-soloed).

        Call this whenever a Mute or Solo button changes. A part that's
        un-muted is heard again from its next note.
        """
        for channel, pitch in list(self.sounding):  # a copy: we change the set inside the loop
            if not self.is_audible(CHANNELS.index(channel)):
                self.synth.noteoff(channel, pitch)
                self.sounding.discard((channel, pitch))

    def preview(self, program, pitch):
        """Play one short note on the preview channel (works while playing, too)."""
        self.end_preview()  # cut off the previous preview, if it's still sounding
        self.synth.program_select(PREVIEW_CHANNEL, self.soundfont_id, 0, program)
        self.synth.noteon(PREVIEW_CHANNEL, pitch, PREVIEW_VELOCITY)
        self.preview_pitch = pitch
        self.preview_timer.start(round(PREVIEW_SECONDS * 1000))

    def end_preview(self):
        """Stop the preview note, if there is one."""
        if self.preview_pitch is not None:
            self.synth.noteoff(PREVIEW_CHANNEL, self.preview_pitch)
            self.preview_pitch = None
        self.preview_timer.stop()

    def release_all(self):
        """Stop every note that is sounding."""
        for channel, pitch in self.sounding:
            self.synth.noteoff(channel, pitch)
        self.sounding.clear()

    def close(self):
        """Shut the synthesizer down. Call once, when the app exits."""
        self.stop()
        self.end_preview()
        self.synth.delete()
