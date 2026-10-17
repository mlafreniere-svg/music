"""The music itself: notes, durations, and parts.

This file knows nothing about windows, drawing, or sound. Keeping it separate
means the drawing code, playback code, and save/load code can all share the
same data without getting tangled together.
"""

import math
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


def fit_octave_shift(steps):
    """How far (in whole octaves of 7 steps) to move notes so their average
    sits as close as possible to the middle line of the staff."""
    if not steps:
        return 0
    average = sum(steps) / len(steps)
    return -7 * round((average - STAFF_MIDDLE_STEP) / 7)


def spell(midi, clef, letter):
    """Write a MIDI pitch as a staff step + alter, using the given letter
    (C=0 ... B=6) if it can be done with at most one ♯ or ♭.

    Returns (step, alter). If that letter would need a double sharp or
    flat, the nearest letter that works is used instead.
    """
    best = None
    for step in range(-60, 61):  # every step from far below to far above the staff
        alter = midi - step_to_midi(step, clef)
        if abs(alter) > 1:
            continue  # too far: this step can't spell the pitch
        score = (letter_of(step, clef) != letter, abs(alter))  # prefer the letter, then fewer signs
        if best is None or score < best[0]:  # tuples compare item by item
            best = (score, step, alter)
    return best[1], best[2]


# How many letters a written note moves when it moves by this many half steps
# (0-11), e.g. 2 half steps (a whole step) is 1 letter: C -> D.
LETTERS_FOR_SEMITONES = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6]


def transpose_note(step, alter, clef, semitones):
    """Move a written note by some half steps, spelled the way musicians would.

    Returns the new (step, alter). The letter moves by the matching interval,
    so a C moved down 2 half steps becomes B-flat (not A-sharp).
    """
    if semitones == 0:
        return step, alter
    # Whole octaves move 7 letters each; the rest uses the table above.
    # (Floor division keeps this right for negative moves: -2 is -1 octave + 10.)
    letters = 7 * (semitones // 12) + LETTERS_FOR_SEMITONES[semitones % 12]
    pitch = step_to_midi(step, clef) + alter + semitones
    return spell(pitch, clef, (letter_of(step, clef) + letters) % 7)


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
    # Transposing instruments sound at a different pitch than written:
    # sounding = written + transpose (in half steps). A guitar sounds an
    # octave lower than written (-12); a B-flat trumpet a whole step lower (-2).
    transpose: int = 0
    # Which bank of the SoundFont the sound comes from. Bank 0 holds the
    # normal instruments; bank 128 holds the drum kits.
    bank: int = 0

    @property
    def is_drums(self):
        return self.clef == PERCUSSION

    @property
    def concert_offset(self):
        """How far (in half steps) "concert pitch" view moves this part's notes.

        It's the transposition without whole octaves: a trumpet (-2) shows
        notes a whole step lower; a tenor sax (-14) also -2; guitars and
        basses (-12) don't move, as in notation programs (an octave down
        would bury them in ledger lines).
        """
        return int(math.fmod(self.transpose, 12))  # fmod keeps the sign: fmod(-14, 12) is -2


# --- Drums ---------------------------------------------------------------
# On a drum staff each line or space means a different drum, not a pitch.

PERCUSSION = "percussion"  # the clef name for drum parts
DRUM_BANK = 128


@dataclass(frozen=True)
class Drum:
    name: str
    key: int      # the General MIDI drum sound: which drum the kit plays
    cymbal: bool  # cymbals are written with x-shaped note heads


# Staff step -> drum, in standard drum notation (steps as on a treble staff).
DRUM_MAP = {
    10: Drum("Crash cymbal", 49, True),   # A5, on a ledger line above the staff
    9: Drum("Hi-hat", 42, True),          # G5, the space above the staff
    8: Drum("Ride cymbal", 51, True),     # F5, the top line
    7: Drum("High tom", 50, False),       # E5
    6: Drum("Mid tom", 47, False),        # D5
    5: Drum("Snare drum", 38, False),     # C5, the third space
    3: Drum("Floor tom", 43, False),      # A4, the second space
    1: Drum("Kick (bass drum)", 36, False),  # F4, the bottom space
    -1: Drum("Hi-hat pedal", 44, True),   # D4, just below the staff
}


def nearest_drum_step(step):
    """The closest staff step that has a drum (clicks on a drum staff snap to it)."""
    return min(DRUM_MAP, key=lambda drum_step: abs(drum_step - step))


# The instruments the "+" menu offers, in groups (the menu shows the headings).
PIANO = Instrument("Piano", 0, "treble")
INSTRUMENT_GROUPS = [
    ("Treble clef", [
        PIANO,
        Instrument("Organ", 19, "treble"),
        Instrument("Harp", 46, "treble"),
        Instrument("Violin", 40, "treble"),
        Instrument("Flute", 73, "treble"),
        Instrument("Oboe", 68, "treble"),
        Instrument("Marimba", 12, "treble"),
        Instrument("Choir", 52, "treble"),
    ]),
    ("Transposing (written ≠ sounding)", [
        Instrument("Acoustic Guitar", 25, "treble", -12),
        Instrument("Electric Guitar", 27, "treble", -12),
        Instrument("Distortion Guitar", 30, "treble", -12),
        Instrument("Trumpet in B♭", 56, "treble", -2),
        Instrument("Horn in F", 60, "treble", -7),
        Instrument("Clarinet in B♭", 71, "treble", -2),
        Instrument("Alto Sax", 65, "treble", -9),
        Instrument("Tenor Sax", 66, "treble", -14),
        Instrument("Bass Guitar", 33, "bass", -12),
        Instrument("Double Bass", 43, "bass", -12),
    ]),
    ("Bass clef", [
        Instrument("Piano (bass)", 0, "bass"),
        Instrument("Cello", 42, "bass"),
        Instrument("Bassoon", 70, "bass"),
        Instrument("Trombone", 57, "bass"),
        Instrument("Tuba", 58, "bass"),
    ]),
    ("Percussion", [
        Instrument("Drum Kit", 0, PERCUSSION, bank=DRUM_BANK),  # program 0 = the standard kit
    ]),
]
# All instruments in one list: a "nested" comprehension, with two for's.
INSTRUMENTS = [instrument for _, group in INSTRUMENT_GROUPS for instrument in group]


def rewrite_for_instrument(notes, old, new):
    """The notes' new (step, alter) when switching from instrument `old` to `new`.

    The sound is kept: each note is respelled so the new instrument plays the
    same note names (in sound), then the whole part moves by octaves to sit
    well on the new staff. Rests come back as None.
    """
    if old.clef == new.clef and old.transpose == new.transpose:
        return [None if n.is_rest else (n.step, n.alter) for n in notes]
    if old.is_drums or new.is_drums:
        # Drums have no pitch, so there's no sound to keep: notes keep their
        # place on the staff (snapped to a drum when going to drums).
        snap = nearest_drum_step if new.is_drums else (lambda step: step)
        return [None if n.is_rest else (snap(n.step), NATURAL) for n in notes]
    # How much higher the new instrument's written notes are (0-11 half steps,
    # ignoring octaves), and so how many letters they move.
    letters_up = LETTERS_FOR_SEMITONES[(old.transpose - new.transpose) % 12]
    spelled = []
    for note in notes:
        if note.is_rest:
            spelled.append(None)
            continue
        sounding = step_to_midi(note.step, old.clef) + note.alter + old.transpose
        written = sounding - new.transpose
        letter = (letter_of(note.step, old.clef) + letters_up) % 7
        spelled.append(spell(written, new.clef, letter))
    shift = fit_octave_shift([step for step, _ in filter(None, spelled)])  # filter(None, ...) skips rests
    return [None if s is None else (s[0] + shift, s[1]) for s in spelled]


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

    def sounding_pitch(self, note):
        """The MIDI pitch this note actually sounds at (None for a rest).

        For transposing instruments this differs from the written pitch.
        """
        if note.is_rest:
            return None
        if self.instrument.is_drums:
            return DRUM_MAP[nearest_drum_step(note.step)].key  # which drum to hit
        return note.midi_pitch(self.clef) + self.instrument.transpose

    def written_key(self, concert_key):
        """The key signature this part shows, for a piece in `concert_key`.

        A B-flat trumpet's part is written a whole step higher, so a piece
        in C major shows D major (2 sharps) on the trumpet's staff.
        Drum parts never have a key signature.
        """
        if self.instrument.is_drums:
            return 0
        # Moving up by 1 half step adds 7 sharps (or removes 5 flats) to a key,
        # so moving the written notes up by -transpose half steps adds this many:
        key = concert_key + (-self.instrument.transpose * 7) % 12
        while key > 7:   # e.g. "8 sharps" is better written as 4 flats
            key -= 12
        return key

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
        if self.instrument.is_drums:
            return [None] * len(self.notes)  # drums have no sharps or flats
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

    def pieces(self):
        """How to *write* the notes: each note split into drawable pieces.

        A note that doesn't fit in what's left of its measure is split at the
        bar line, and the pieces are joined by ties: a half note starting on
        beat 4 is written as two quarter notes, tied. Lengths that aren't a
        single note value (like 3 beats) are split too (half + quarter).
        Rests are split the same way, but rests are never tied.

        The notes themselves don't change: a tied half note still *sounds*
        like one half note. This only decides how it's drawn.
        """
        pieces = []
        beat = 0.0
        for index, note in enumerate(self.notes):
            first_piece = len(pieces)
            remaining = note.duration
            while remaining > 0:
                # % is the remainder: how far into the current measure we are.
                room = BEATS_PER_MEASURE - beat % BEATS_PER_MEASURE
                for length in split_duration(min(remaining, room)):
                    beat += length
                    remaining -= length
                    pieces.append(Piece(
                        note_index=index,
                        duration=length,
                        first=len(pieces) == first_piece,
                        tied=False,
                        ends_measure=beat % BEATS_PER_MEASURE == 0,
                    ))
            if not note.is_rest:
                # Tie every piece of this note to the next one, except the last.
                for piece in pieces[first_piece:-1]:
                    piece.tied = True
        return pieces


@dataclass
class Piece:
    """One drawn symbol: all or part of a note (see Part.pieces)."""

    note_index: int     # which note this is a piece of
    duration: float     # a single note value: WHOLE, HALF, QUARTER, or EIGHTH
    first: bool         # the note's first piece (where its ♯ ♭ ♮ goes)
    tied: bool          # a tie joins this piece to the next one
    ends_measure: bool  # a bar line comes right after this piece


NOTE_VALUES = [WHOLE, HALF, QUARTER, EIGHTH]  # longest first


def split_duration(beats):
    """Split a length into note values, longest first: 3 beats -> [2.0, 1.0]."""
    parts = []
    for value in NOTE_VALUES:
        while beats >= value:
            parts.append(value)
            beats -= value
    return parts


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
                pitch = part.sounding_pitch(note)  # what you hear, not what's written
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
