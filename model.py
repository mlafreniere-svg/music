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


@dataclass
class Part:
    """The music for one instrument: its notes, in order."""

    # field(default_factory=list) gives every Part its own new, empty list.
    # (Writing "notes: list = []" would make all parts share one list, a
    # classic Python mistake, so dataclasses don't allow it.)
    notes: list[Note] = field(default_factory=list)

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
