"""Undoable edits: every change to the music is a command that can undo itself.

This is the "command pattern". Instead of changing the music directly, the
app creates a small object describing the change and pushes it onto a
QUndoStack. The stack calls redo() to make the change, and later undo() to
reverse it, or redo() again to repeat it.

Each command keeps exactly what it needs to work both ways: a deleted note
remembers itself and its position, a moved note remembers both pitches.

Every command also gets a "view" (the main window) with these methods, so it
can show its change on screen:
    view.part_changed(part, index)  redraw the part's tab; show note `index`
    view.instrument_changed(part)   relabel the part's tab and redraw its clef
    view.insert_part(index, part)   add a tab for this part at `index`
    view.remove_part_at(index)      remove the tab (and part) at `index`
    view.set_tempo(bpm)             change the tempo and move the slider
    view.set_key(key)               change the key signature and the Key dropdown
"""

from PySide6.QtGui import QUndoCommand

from model import Part, rewrite_for_instrument


class AddNote(QUndoCommand):
    """Add a note (or rest) at the end of a part."""

    def __init__(self, view, part, note):
        # The text shows up in the Edit menu: "Undo Add note".
        super().__init__("Add rest" if note.is_rest else "Add note")
        self.view = view
        self.part = part
        self.note = note
        self.index = len(part.notes)  # where the note goes: the end, right now

    def redo(self):
        self.part.insert_note(self.index, self.note)
        self.view.part_changed(self.part, self.index)

    def undo(self):
        self.part.remove_note(self.index)
        self.view.part_changed(self.part, self.index - 1)


class RemoveNote(QUndoCommand):
    """Delete the note at a position (right-click or Backspace)."""

    def __init__(self, view, part, index):
        super().__init__("Delete note")
        self.view = view
        self.part = part
        self.index = index
        self.note = part.notes[index]  # remember it, so undo can put it back

    def redo(self):
        self.part.remove_note(self.index)
        self.view.part_changed(self.part, self.index - 1)

    def undo(self):
        self.part.insert_note(self.index, self.note)
        self.view.part_changed(self.part, self.index)


class MoveNote(QUndoCommand):
    """Change a note's pitch (by dragging it)."""

    def __init__(self, view, part, index, old_step, new_step):
        super().__init__("Move note")
        self.view = view
        self.part = part
        self.index = index
        self.old_step = old_step
        self.new_step = new_step

    def redo(self):
        self.part.notes[self.index].step = self.new_step
        self.view.part_changed(self.part, self.index)

    def undo(self):
        self.part.notes[self.index].step = self.old_step
        self.view.part_changed(self.part, self.index)


class ChangeAlter(QUndoCommand):
    """Raise or lower a note by a half step (♭ → ♮ → ♯ or back)."""

    def __init__(self, view, part, index, new_alter):
        old_alter = part.notes[index].alter
        super().__init__("Raise note" if new_alter > old_alter else "Lower note")
        self.view = view
        self.part = part
        self.index = index
        self.old_alter = old_alter
        self.new_alter = new_alter

    def redo(self):
        self.part.notes[self.index].alter = self.new_alter
        self.view.part_changed(self.part, self.index)

    def undo(self):
        self.part.notes[self.index].alter = self.old_alter
        self.view.part_changed(self.part, self.index)


class ChangeInstrument(QUndoCommand):
    """Switch a part to another instrument, keeping how it sounds.

    Notes are respelled for the new instrument (its clef and transposition)
    and moved by octaves to fit its staff (see rewrite_for_instrument).
    """

    def __init__(self, view, part, instrument):
        super().__init__(f"Change to {instrument.name}")
        self.view = view
        self.part = part
        self.old_instrument = part.instrument
        self.new_instrument = instrument
        # Remember every note's (step, alter) before and after, so undo is exact.
        self.old_spelling = [None if n.is_rest else (n.step, n.alter) for n in part.notes]
        self.new_spelling = rewrite_for_instrument(part.notes, part.instrument, instrument)

    def apply(self, instrument, spelling):
        """Set the instrument and give every pitched note its (step, alter)."""
        self.part.instrument = instrument
        # zip pairs up two lists item by item: (note 0, spelling 0), (note 1, ...), ...
        for note, spelled in zip(self.part.notes, spelling):
            if spelled is not None:
                note.step, note.alter = spelled  # unpack the pair into two fields
        self.view.instrument_changed(self.part)

    def redo(self):
        self.apply(self.new_instrument, self.new_spelling)

    def undo(self):
        self.apply(self.old_instrument, self.old_spelling)


class AddPart(QUndoCommand):
    """Add an instrument tab."""

    def __init__(self, view, score, instrument):
        super().__init__(f"Add {instrument.name}")
        self.view = view
        self.part = Part(instrument=instrument)
        self.index = len(score.parts)  # new tabs go at the end

    def redo(self):
        self.view.insert_part(self.index, self.part)

    def undo(self):
        self.view.remove_part_at(self.index)


class RemovePart(QUndoCommand):
    """Close an instrument tab. Undo brings it back, notes and all."""

    def __init__(self, view, score, index):
        part = score.parts[index]
        super().__init__(f"Remove {part.instrument.name}")
        self.view = view
        self.part = part  # keeping the Part keeps all its notes, too
        self.index = index

    def redo(self):
        self.view.remove_part_at(self.index)

    def undo(self):
        self.view.insert_part(self.index, self.part)


class ChangeKey(QUndoCommand):
    """Change the key signature. Notes keep their pitches; only signs change."""

    def __init__(self, view, old_key, new_key):
        super().__init__("Change key")
        self.view = view
        self.old_key = old_key
        self.new_key = new_key

    def redo(self):
        self.view.set_key(self.new_key)

    def undo(self):
        self.view.set_key(self.old_key)


class ChangeTempo(QUndoCommand):
    """Change the tempo. One drag of the slider becomes ONE undo step."""

    def __init__(self, view, old_bpm, new_bpm):
        super().__init__("Change tempo")
        self.view = view
        self.old_bpm = old_bpm
        self.new_bpm = new_bpm

    def id(self):
        # Commands with the same id (other than -1) may be merged together.
        return 1

    def mergeWith(self, other):
        # Called by the stack when another ChangeTempo comes right after this
        # one: take its new tempo, keep our old one, and report success.
        self.new_bpm = other.new_bpm
        return True

    def redo(self):
        self.view.set_tempo(self.new_bpm)

    def undo(self):
        self.view.set_tempo(self.old_bpm)
