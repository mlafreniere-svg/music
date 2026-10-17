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


STAFF_MIDDLE_STEP = 4  # the middle line of the staff

# Accidentals: how far a note is raised or lowered from its letter, in half steps.
FLAT = -1
NATURAL = 0
SHARP = 1

# Key signatures are stored as a number: positive = that many sharps,
# negative = that many flats (e.g. 1 = G major, -2 = B-flat major).
# Sharps are always added in this order of letters, flats in the reverse.
# Letters are numbered C=0, D=1, E=2, F=3, G=4, A=5, B=6.
SHARP_ORDER = [3, 0, 4, 1, 5, 2, 6]  # F C G D A E B
FLAT_ORDER = [6, 2, 5, 1, 4, 0, 3]   # B E A D G C F


# Every key signature, from 7 flats to 7 sharps: (major key, its relative minor).
# A major key and its relative minor share the same sharps or flats.
KEY_NAMES = {
    -7: ("C♭ major", "A♭ minor"),
    -6: ("G♭ major", "E♭ minor"),
    -5: ("D♭ major", "B♭ minor"),
    -4: ("A♭ major", "F minor"),
    -3: ("E♭ major", "C minor"),
    -2: ("B♭ major", "G minor"),
    -1: ("F major", "D minor"),
    0: ("C major", "A minor"),
    1: ("G major", "E minor"),
    2: ("D major", "B minor"),
    3: ("A major", "F♯ minor"),
    4: ("E major", "C♯ minor"),
    5: ("B major", "G♯ minor"),
    6: ("F♯ major", "D♯ minor"),
    7: ("C♯ major", "A♯ minor"),
}


def key_name(key):
    """A readable name for a key signature, e.g. "G major / E minor (1♯)"."""
    major, minor = KEY_NAMES[key]  # "unpacking": a pair of values into two names
    if key == 0:
        count = "no ♯ or ♭"
    elif key > 0:
        count = f"{key}♯"
    else:
        count = f"{-key}♭"
    return f"{major} / {minor} ({count})"


def letter_of(step, clef):
    """Which letter (C=0 ... B=6) a staff step is in this clef."""
    return (step + CLEF_BOTTOM_LINE[clef]) % 7


def key_alter(letter, key):
    """How the key signature alters this letter: SHARP, FLAT, or NATURAL."""
    if key > 0 and letter in SHARP_ORDER[:key]:  # [:key] = the first `key` items
        return SHARP
    if key < 0 and letter in FLAT_ORDER[:-key]:
        return FLAT
    return NATURAL


def clef_change_shift(steps, old_clef, new_clef):
    """How far (in staff steps) to move notes when their clef changes.

    The notes keep their letter names (an E stays an E) and move by whole
    octaves to sit as close as possible to the middle of the new staff.
    `steps` are the pitched notes' steps (no rests).
    """
    if old_clef == new_clef:
        return 0
    # Moving by this many steps would keep the exact same pitches:
    # treble -> bass is 2 - (-10) = 12 steps (the same sound sits higher on a bass staff).
    same_pitch = CLEF_BOTTOM_LINE[old_clef] - CLEF_BOTTOM_LINE[new_clef]
    if steps:
        average = sum(steps) / len(steps)
    else:
        average = STAFF_MIDDLE_STEP  # no notes: any octave will do
    # An octave is 7 letters (steps). Take away whole octaves until the
    # notes' average is as close as possible to the middle line.
    octaves = round((average + same_pitch - STAFF_MIDDLE_STEP) / 7)
    return same_pitch - 7 * octaves


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
    # FLAT (-1), NATURAL (0) or SHARP (+1): the note's real pitch relative to
    # its letter. Whether a sign is *drawn* is decided separately (see
    # Part.accidental_signs), the way printed music does it.
    alter: int = NATURAL

    @property
    def is_rest(self):
        """True if this is a rest. Use it like a value: note.is_rest"""
        return self.step is None

    def midi_pitch(self, clef="treble"):
        """This note's MIDI pitch, or None for a rest."""
        if self.is_rest:
            return None
        return step_to_midi(self.step, clef) + self.alter


@dataclass
class Part:
    """The music for one instrument: its notes, in order."""

    # field(default_factory=list) gives every Part its own new, empty list.
    # (Writing "notes: list = []" would make all parts share one list, a
    # classic Python mistake, so dataclasses don't allow it.)
    notes: list[Note] = field(default_factory=list)
    # Sharing one Instrument is fine (unlike a list), because it's frozen.
    instrument: Instrument = PIANO
    muted: bool = False   # Mute: silence this part
    soloed: bool = False  # Solo: play only the soloed parts

    @property
    def clef(self):
        """The clef this part is written in; it comes from the instrument."""
        return self.instrument.clef

    def add_note(self, note):
        """Add a note (or rest) to the end of the part."""
        self.notes.append(note)

    def insert_note(self, index, note):
        """Put a note at this position; the notes from there on move right.

        Undo uses this to put a deleted note back exactly where it was.
        """
        self.notes.insert(index, note)

    def remove_note(self, index):
        """Remove the note at this position (0 = first). Later notes move left."""
        del self.notes[index]

    def remove_last(self):
        """Remove the last note, if there is one."""
        if self.notes:  # an empty list counts as False, so this means "if not empty"
            self.notes.pop()  # pop() removes the last item of a list

    def accidental_signs(self, key=0):
        """Which accidental sign to draw in front of each note, if any.

        Returns one entry per note: None (draw nothing), or SHARP, FLAT, or
        NATURAL (draw that sign). Standard rule: the key signature says what
        each letter normally is; an accidental changes that line or space
        for the rest of its measure; a bar line resets everything.
        """
        signs = []
        current = {}  # staff step -> its alter so far in this measure
        beats = 0.0
        measure = 0
        for note in self.notes:
            if beats // BEATS_PER_MEASURE != measure:  # crossed into a new measure
                measure = beats // BEATS_PER_MEASURE
                current = {}  # back to the key signature
            sign = None
            if not note.is_rest:
                expected = current.get(note.step, key_alter(letter_of(note.step, self.clef), key))
                if note.alter != expected:
                    sign = note.alter  # different from what the reader expects: show it
                current[note.step] = note.alter
            signs.append(sign)
            beats += note.duration
        return signs

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


@dataclass(frozen=True)
class Event:
    """One moment in a performance: a note starting or ending."""

    beat: float       # when it happens, counted in beats from the start
    starts: bool      # True: the note begins here; False: it ends here
    part_index: int   # which part (tab) the note belongs to
    note_index: int   # which note in that part
    pitch: int | None # MIDI pitch, or None for a rest


@dataclass
class Score:
    """A whole piece: one Part per instrument, all played together."""

    parts: list[Part] = field(default_factory=list)
    tempo_bpm: int = 100  # beats (quarter notes) per minute; saved with the piece
    key: int = 0          # key signature: + sharps, - flats (0 = C major, no sharps or flats)

    def is_audible(self, part_index):
        """Should this part be heard, given everyone's Mute and Solo buttons?

        If any part is soloed, only soloed parts play (solo wins over mute).
        Otherwise, every part plays except the muted ones.
        """
        part = self.parts[part_index]
        # any(...) is True if at least one item is True.
        if any(p.soloed for p in self.parts):
            return part.soloed
        return not part.muted

    def timeline(self):
        """Every note's start and end in every part, as one list sorted by beat.

        This is how the parts play "together": the player walks through one
        list instead of juggling separate ones.
        """
        events = []
        for part_index, part in enumerate(self.parts):
            beat = 0.0
            for note_index, note in enumerate(part.notes):
                pitch = note.midi_pitch(part.clef)
                events.append(Event(beat, True, part_index, note_index, pitch))
                beat += note.duration
                events.append(Event(beat, False, part_index, note_index, pitch))
        # Sort by beat. At the same beat, endings (starts=False) come before
        # beginnings (starts=True), because False sorts before True. So a
        # repeated note is released before it's played again.
        events.sort(key=lambda event: (event.beat, event.starts))
        return events

    def add_part(self, instrument):
        """Add an empty part for this instrument and return it."""
        part = Part(instrument=instrument)  # a keyword argument: skip notes, set instrument
        self.parts.append(part)
        return part

    def insert_part(self, index, part):
        """Put a part at this position (undo uses this to restore a closed tab)."""
        self.parts.insert(index, part)

    def remove_part(self, index):
        """Remove the part at this position (0 = first)."""
        del self.parts[index]
