"""The music itself: notes, durations, and parts.

This file knows nothing about windows, drawing, or sound. Keeping it separate
means the drawing code, playback code, and save/load code can all share the
same data without getting tangled together.
"""

from dataclasses import dataclass, field

# Durations, measured in beats. In 4/4 time a quarter note gets one beat.
WHOLE = 4.0
HALF = 2.0
QUARTER = 1.0
EIGHTH = 0.5

BEATS_PER_MEASURE = 4  # 4/4 time: four quarter-note beats in every measure

# --- Pitch ---------------------------------------------------------------
# MIDI numbers every key on a piano: 60 is middle C (C4), and each +1 is one
# half step higher (one piano key, black or white).
MIDDLE_C = 60

# How many half steps above C each letter is: C D E F G A B.
# The gaps are uneven (E-F and B-C are only 1 half step), which is why we
# need this table instead of just multiplying.
LETTER_SEMITONES = [0, 2, 4, 5, 7, 9, 11]

# For each clef: how many letters the bottom staff line is above middle C.
# Treble: bottom line is E4, 2 letters above C4 (C, D, E).
# Bass:   bottom line is G2, 10 letters below C4.
CLEF_BOTTOM_LINE = {
    "treble": 2,
    "bass": -10,
}


def step_to_midi(step, clef="treble"):
    """Convert a staff step (0 = bottom line) to a MIDI pitch number."""
    letters_above_c4 = step + CLEF_BOTTOM_LINE[clef]
    # Split into whole octaves plus a letter within the octave (0-6).
    # Floor division // and remainder % work for negative numbers too:
    # -1 // 7 is -1 and -1 % 7 is 6, i.e. "one octave down, letter B".
    octave = letters_above_c4 // 7
    letter = letters_above_c4 % 7
    return MIDDLE_C + 12 * octave + LETTER_SEMITONES[letter]


# --- Instruments ---------------------------------------------------------

@dataclass(frozen=True)
class Instrument:
    """An instrument a part can be played on.

    frozen=True makes it read-only: once created, an Instrument can't be
    changed. That makes it safe for many parts to share the same one.
    """

    name: str     # shown on the tab
    program: int  # General MIDI program number, 0-127 (0 = Acoustic Grand Piano)
    clef: str     # "treble" or "bass": which clef its music is written in


# The instruments the "+" menu offers. All of them sound at the written
# pitch; transposing instruments (trumpet, clarinet...) are left out for now.
PIANO = Instrument("Piano", 0, "treble")
INSTRUMENTS = [
    PIANO,
    Instrument("Organ", 19, "treble"),
    Instrument("Harp", 46, "treble"),
    Instrument("Violin", 40, "treble"),
    Instrument("Flute", 73, "treble"),
    Instrument("Oboe", 68, "treble"),
    Instrument("Marimba", 12, "treble"),
    Instrument("Choir", 52, "treble"),
    Instrument("Piano (bass)", 0, "bass"),
    Instrument("Cello", 42, "bass"),
    Instrument("Bassoon", 70, "bass"),
    Instrument("Trombone", 57, "bass"),
    Instrument("Tuba", 58, "bass"),
]


def find_instrument(name):
    """Look up an instrument in INSTRUMENTS by its name."""
    for instrument in INSTRUMENTS:
        if instrument.name == name:
            return instrument
    raise ValueError(f"No instrument named {name!r}")  # stops with a clear error


# --- Notes, parts, and the score -----------------------------------------

@dataclass
class Note:
    """One note or rest.

    @dataclass writes the boring parts of the class for us: Note(4, HALF)
    automatically stores step=4 and duration=HALF, and printing a note
    shows something readable like Note(step=4, duration=2.0).
    """

    # Staff step: 0 is the bottom line, 1 the space above it, and so on.
    # None means "no pitch", which is how we represent a rest.
    step: int | None
    duration: float = QUARTER  # used when no duration is given: Note(4)

    @property
    def is_rest(self):
        """True if this is a rest. Use it like a value: note.is_rest"""
        return self.step is None

    def midi_pitch(self, clef="treble"):
        """This note's MIDI pitch, or None for a rest."""
        if self.is_rest:
            return None
        return step_to_midi(self.step, clef)


@dataclass
class Part:
    """The music for one instrument: its notes, in order."""

    # field(default_factory=list) gives every Part its own new, empty list.
    # (Writing "notes: list = []" would make all parts share one list, a
    # classic Python mistake, so dataclasses don't allow it.)
    notes: list[Note] = field(default_factory=list)
    # Sharing one Instrument is fine (unlike a list), because it's frozen.
    instrument: Instrument = PIANO

    @property
    def clef(self):
        """The clef this part is written in; it comes from the instrument."""
        return self.instrument.clef

    def add_note(self, note):
        """Add a note (or rest) to the end of the part."""
        self.notes.append(note)

    def remove_note(self, index):
        """Remove the note at this position (0 = first). Later notes move left."""
        del self.notes[index]

    def remove_last(self):
        """Remove the last note, if there is one."""
        if self.notes:  # an empty list counts as False, so this means "if not empty"
            self.notes.pop()  # pop() removes the last item of a list

    def measure_ends(self):
        """The positions (indexes) of the notes that finish a measure.

        A bar line belongs right after each of these notes. We add up the
        beats as we go; whenever the total passes into a new measure, the
        note that got us there ends the old one.
        """
        ends = []
        beats = 0.0
        for index, note in enumerate(self.notes):
            # // is "floor division": divide and drop the remainder.
            # 7 // 4 is 1, so beat 7 is in measure 1 (counting from 0).
            measure_before = beats // BEATS_PER_MEASURE
            beats += note.duration
            if beats // BEATS_PER_MEASURE > measure_before:
                ends.append(index)
        return ends


@dataclass
class Score:
    """A whole piece: one Part per instrument, all played together."""

    parts: list[Part] = field(default_factory=list)

    def add_part(self, instrument):
        """Add an empty part for this instrument and return it."""
        part = Part(instrument=instrument)  # a keyword argument: skip notes, set instrument
        self.parts.append(part)
        return part

    def remove_part(self, index):
        """Remove the part at this position (0 = first)."""
        del self.parts[index]
