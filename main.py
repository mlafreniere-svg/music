"""Music staff app: the program's starting point. Run with: python main.py"""

import bisect
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QFontMetricsF, QKeySequence, QPainter,
    QPainterPath, QPen, QUndoStack,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox,
    QScrollArea, QSlider, QTabBar, QTabWidget, QToolButton, QVBoxLayout, QWidget,
)

from model import (  # our own model.py
    COMMON_TIME, DOTTABLE, DRUM_MAP, EIGHTH, FLAT, GRAND_PIANO, HALF, INSTRUMENT_GROUPS,
    KEY_NAMES, NATURAL, QUARTER, SHARP, TIME_SIGNATURES, WHOLE, Note, Part, Score, key_alter,
    key_name, letter_of, measure_length, nearest_drum_step, transpose_note, undotted,
)
from edits import (
    AddNote, AddPart, ChangeInstrument, ChangeKey, ChangeTempo, ChangeTimeSignature,
    RemoveNote, RemovePart, SetNotePitch,
)
from midi_export import export_midi
from player import MAX_PARTS, PAUSED, PLAYING, STOPPED, Player
from storage import FILE_EXTENSION, display_name, load_score, save_score

# What the Open and Save dialogs show. Each ";;"-separated entry is one
# choice in the dialog's file-type dropdown.
FILE_FILTER = f"Music Staff files (*{FILE_EXTENSION});;All files (*)"

# Where scores are saved by default: a folder inside the project.
SAVED_MUSIC_FOLDER = Path(__file__).parent / "saved_music"

# Layout measurements, in pixels. Keeping them as named constants (instead of
# typing numbers everywhere) means one change here updates the whole drawing.
LINE_SPACING = 16  # distance between two staff lines
STAFF_TOP = 60     # y position of the top staff line (y grows downward!)
MARGIN = 40        # empty space at the left and right edges

# Note size, based on LINE_SPACING so notes grow and shrink with the staff.
NOTE_HEAD_WIDTH = LINE_SPACING * 1.3   # note heads are slightly wider than tall
NOTE_HEAD_HEIGHT = LINE_SPACING        # exactly fills one space between lines
STEM_LENGTH = LINE_SPACING * 3.5

# Horizontal layout: notes are placed left to right, one after another.
FIRST_NOTE_X = MARGIN + 90  # leaves room at the start for the clef (and a first ♯ or ♭)
NOTE_SPACING = 40           # distance from one note to the next
EMPTY_SPACE_AT_END = NOTE_SPACING * 8 + MARGIN  # room after the last note to click into

# Pitches are stored as "staff steps": 0 is the bottom line, 1 the space
# above it, 2 the next line, and so on (half a LINE_SPACING per step).
# In treble clef, step 0 is E4 and step -2 is middle C.
STEP_HEIGHT = LINE_SPACING / 2
BOTTOM_LINE_Y = STAFF_TOP + 4 * LINE_SPACING
TOP_LINE_STEP = 8   # the 5 lines are steps 0, 2, 4, 6, 8
MIDDLE_LINE_STEP = 4
LOWEST_STEP = -2    # middle C, one ledger line below the staff
HIGHEST_STEP = 10   # A5, one ledger line above the staff

# The duration buttons: (label, duration, keyboard shortcut).
# Adding a duration later only means adding a line here.
DURATION_CHOICES = [
    ("Whole", WHOLE, "1"),
    ("Half", HALF, "2"),
    ("Quarter", QUARTER, "3"),
    ("Eighth", EIGHTH, "4"),
]

# Playback cursor: a see-through band behind the note that's playing.
# QColor(red, green, blue, alpha): alpha 0 is invisible, 255 is solid.
CURSOR_COLOR = QColor(70, 130, 230, 60)

# Staffs are drawn in INK; parts that are silenced by Mute/Solo in DIMMED_INK.
INK = QColor(0, 0, 0)
DIMMED_INK = QColor(170, 170, 170)

# Colors for the Mute and Solo buttons when they're switched on. This is a
# Qt "style sheet": the same idea as CSS on web pages.
MUTE_SOLO_STYLE = """
QToolButton { padding: 0px 3px; font-weight: bold; }
QToolButton#mute:checked { background: #e05050; color: white; }
QToolButton#solo:checked { background: #f0c030; color: black; }
"""

# Clef symbols are characters in the "Segoe UI Symbol" font that comes with
# Windows. \U0001D11E is the character's Unicode number (its ID in a
# worldwide table of every character).
CLEF_SYMBOLS = {
    "treble": "\U0001D11E",  # 𝄞
    "bass": "\U0001D122",    # 𝄢
}
CLEF_FONT = "Segoe UI Symbol"
# Where each clef's outline should start and end, in staff steps
# (the top line is step 8, the bottom line step 0):
#   treble rises above the top line and dips below the bottom line;
#   bass runs from the top line down to just above the bottom line.
CLEF_TOP_STEP = {"treble": 10.6, "bass": 8.7}
CLEF_BOTTOM_STEP = {"treble": -3.0, "bass": 1.9}

# Accidental signs, from the same font: sharp, flat, natural.
ACCIDENTAL_SYMBOLS = {SHARP: "♯", FLAT: "♭", NATURAL: "♮"}
# How tall each sign is drawn, in staff spaces (as in printed music).
ACCIDENTAL_HEIGHT = {SHARP: 2.6, FLAT: 2.3, NATURAL: 2.6}

# Key signatures: the staff step of each sharp or flat, in the order they're
# added (sharps F C G D A E B, flats B E A D G C F). Bass clef uses the same
# zig-zag pattern, 2 steps lower.
KEY_SHARP_STEPS = {"treble": [8, 5, 9, 6, 3, 7, 4], "bass": [6, 3, 7, 4, 1, 5, 2]}
KEY_FLAT_STEPS = {"treble": [4, 7, 3, 6, 2, 5, 1], "bass": [2, 5, 1, 4, 0, 3, -1]}
DRUM_CLEF_WIDTH = LINE_SPACING * 0.9   # the percussion clef's two bars, side to side
TIME_SIGNATURE_FONT = "Times New Roman"  # bold serif numbers, as in printed music
TIME_GAP = 8                           # space between the key signature and the time signature
KEY_GAP = 6                            # space between the clef and the key signature
KEY_SIGN_SPACING = LINE_SPACING * 1.25  # distance between the key's signs (a sharp is ~1 space wide)
# After the key signature: half a note head + an accidental + small gaps.
ROOM_BEFORE_FIRST_NOTE = NOTE_HEAD_WIDTH / 2 + LINE_SPACING * 1.6

# The accidental buttons: (button text, tooltip, alter, keyboard shortcut).
# alter None means "whatever the key signature says" (in G major, F -> F♯).
ACCIDENTAL_CHOICES = [
    ("Key", "Follow the key signature", None, "K"),
    ("♮", "Natural", NATURAL, "N"),
    ("♯", "Sharp", SHARP, "S"),
    ("♭", "Flat", FLAT, "F"),
]

MIN_TEMPO = 40   # beats per minute
MAX_TEMPO = 200


@dataclass
class EditSettings:
    """What the next click on any staff will add. The toolbar changes these.

    All the tabs share ONE EditSettings object, so choosing "Half" applies
    to every tab, including tabs added later.
    """

    duration: float = QUARTER
    rest_mode: bool = False  # when True, clicks add rests instead of notes
    preview: bool = True     # when True, you hear each note as you place it
    # Sharp, flat, or natural for the next note; None = follow the key signature.
    alter: int | None = None
    dotted: bool = False     # when True, half and quarter notes are placed dotted


def step_to_y(step):
    """Convert a staff step to a y position on screen."""
    return BOTTOM_LINE_Y - step * STEP_HEIGHT  # minus, because y grows downward


def y_to_step(y):
    """Convert a y position to the nearest staff step, kept within range."""
    step = round((BOTTOM_LINE_Y - y) / STEP_HEIGHT)
    return max(LOWEST_STEP, min(HIGHEST_STEP, step))  # clamp to the allowed range


class StaffWidget(QWidget):
    """A blank area of the window that draws a musical staff.

    It is a subclass of QWidget: it inherits everything a Qt widget can
    already do, and we only add the part that's ours, the drawing.
    """

    # The staff doesn't change the music itself: it *asks*, and the window
    # turns each request into an undoable command (see edits.py).
    add_requested = Signal(object)          # a Note to add at the end ("object": any Python value)
    remove_requested = Signal(int)          # the index of a note to delete
    move_requested = Signal(int, object, object)  # (index, old (step, alter), new (step, alter))

    preview = Signal(int, int, int)  # (sound bank, program, MIDI pitch): "let me hear this note"
    hint = Signal(str)          # a short message for the status bar (e.g. which drum is here)
    activated = Signal()        # this staff was clicked (it becomes the one Backspace acts on)
    scroll_to = Signal(float)   # an x position that should be scrolled into view

    def __init__(self, part, settings):
        # __init__ runs once, when the widget is created.
        super().__init__()  # first, let QWidget set itself up
        # The music being shown. The widget only draws it and edits it;
        # what a note *is* lives in model.py.
        self.part = part
        # The shared EditSettings: which duration, and notes or rests.
        self.settings = settings
        # The index of the note being played, or None when nothing is playing.
        self.playing_index = None
        # The color everything is drawn in; gray when Mute/Solo silences this part.
        self.ink = INK
        # The key signature shown on this staff (+ sharps / - flats); the window keeps it up to date.
        self.key = 0
        # How far (in half steps) the display is moved from the written notes:
        # 0 normally; in concert pitch view, the instrument's concert_offset.
        self.offset = 0
        # On a grand staff: the other staff (they share columns). None otherwise.
        self.partner = None
        # The time signature, drawn after the key, and how long a measure is
        # in quarter-note beats. The window keeps both up to date.
        self.time_signature = COMMON_TIME
        self.measure_beats = measure_length(COMMON_TIME)
        # The notes as they're *shown*. Drawing and clicking use this; edits
        # are converted back to written pitch and applied to self.part.
        self.shown = self.build_shown()
        # Tall enough for ledger-line notes and the playback cursor.
        self.setMinimumHeight(round(step_to_y(LOWEST_STEP - 4)))
        self.update_width()

        # Dragging: which note is being dragged (None = no drag) and where it started.
        self.drag_index = None
        self.drag_start = None       # the dragged note's written (step, alter) before the drag
        self.drag_shown_alter = NATURAL  # its displayed ♯/♭, kept while dragging
        # The note the mouse is over right now (None = none), for the + / - keys.
        self.hover_index = None
        # Normally Qt only reports mouse movement while a button is held down.
        # Tracking reports it all the time, so we can change the pointer when
        # it's over a note.
        self.setMouseTracking(True)

    def update_width(self):
        """Make the staff wide enough for all its notes plus room for more.

        The staff sits inside a scroll area. When the staff is wider than
        the window, the scroll area shows a scroll bar.
        """
        columns = len(self.column_beats())
        self.setMinimumWidth(round(self.column_x(columns) + EMPTY_SPACE_AT_END))

    def refresh(self):
        """After the part's notes change: rebuild the display, resize, redraw."""
        self.shown = self.build_shown()
        self.update_width()
        self.update()  # ask Qt to repaint soon; it will call paintEvent
        if self.partner is not None:
            # On a grand staff the columns are shared, so the other staff's
            # layout may have changed too.
            self.partner.update_width()
            self.partner.update()

    def set_display(self, offset, key, time_signature):
        """Show the notes moved by `offset` half steps, with key signature `key`
        and the given time signature.

        Written pitch: offset 0 and the part's written key. Concert pitch:
        the instrument's concert offset and the piece's concert key.
        """
        self.offset = offset
        self.key = key
        self.time_signature = time_signature
        self.measure_beats = measure_length(time_signature)
        self.refresh()

    def build_shown(self):
        """A display-only copy of the part, moved by self.offset."""
        if self.offset == 0:
            return self.part  # nothing to change: show the real part
        notes = []
        for note in self.part.notes:
            if note.is_rest:
                notes.append(note)
            else:
                step, alter = self.to_shown(note.step, note.alter)
                notes.append(Note(step, note.duration, alter))
        return Part(notes, self.part.instrument)

    def to_shown(self, step, alter):
        """Written pitch -> how it's displayed."""
        return transpose_note(step, alter, self.part.clef, self.offset)

    def to_written(self, step, alter):
        """Displayed pitch -> written pitch (what's stored)."""
        return transpose_note(step, alter, self.part.clef, -self.offset)

    def set_dimmed(self, dimmed):
        """Draw the staff in gray (dimmed=True) or black."""
        self.ink = DIMMED_INK if dimmed else INK
        self.update()

    def set_playing_index(self, index):
        """Slot: move the playback cursor to this note (None hides it)."""
        self.playing_index = index
        self.update()
        if index is not None:
            self.scroll_to.emit(self.note_x(index))  # keep the cursor in view

    def own_first_note_x(self):
        """Where this staff's first note could go: after its clef, key and time
        signatures, leaving room for a ♯, ♭ or ♮ in front of it."""
        return max(FIRST_NOTE_X, self.time_signature_right() + ROOM_BEFORE_FIRST_NOTE)

    def time_signature_layout(self):
        """The time signature's font, left edge, and width (it follows the key)."""
        font = QFont(TIME_SIGNATURE_FONT)
        font.setBold(True)
        font.setPixelSize(100)
        test_height = QFontMetricsF(font).tightBoundingRect("8").height()
        # Each number is as tall as two staff spaces (half the staff).
        font.setPixelSize(round(100 * LINE_SPACING * 1.9 / test_height))
        metrics = QFontMetricsF(font)
        width = max(metrics.tightBoundingRect(str(n)).width() for n in self.time_signature)
        return font, self.key_signature_right() + TIME_GAP, width

    def time_signature_right(self):
        """Where the time signature ends."""
        _, left, width = self.time_signature_layout()
        return left + width

    def draw_time_signature(self, painter):
        """The two stacked numbers: top in the upper half of the staff, bottom in the lower."""
        font, left, width = self.time_signature_layout()
        metrics = QFontMetricsF(font)
        painter.setFont(font)
        painter.setPen(QPen(self.ink, 1))
        top, bottom = self.time_signature
        for number, (high_step, low_step) in ((top, (8, 4)), (bottom, (4, 0))):
            text = str(number)
            outline = metrics.tightBoundingRect(text)
            middle_y = (step_to_y(high_step) + step_to_y(low_step)) / 2
            baseline = middle_y - (outline.top() + outline.height() / 2)  # centered vertically
            x = left + (width - outline.width()) / 2 - outline.left()    # and horizontally
            painter.drawText(QPointF(x, baseline), text)

    def first_note_x(self):
        """Where the first note goes. On a grand staff both staves use the
        later of their two starting points, so their notes line up."""
        if self.partner is None:
            return self.own_first_note_x()
        return max(self.own_first_note_x(), self.partner.own_first_note_x())

    # The staff is drawn in columns, one for each moment (beat) at which a
    # piece starts (see Part.pieces). On a grand staff the two staves share
    # their columns, so notes played together sit one above the other.
    # A single staff never has two pieces starting together, so there every
    # piece simply gets its own column.

    def pieces(self):
        """The shown notes split into drawable pieces, in this score's measures."""
        return self.shown.pieces(self.measure_beats)

    def column_beats(self):
        """The start beat of every column, in order."""
        beats = {piece.beat for piece in self.pieces()}  # a set: no repeats
        if self.partner is not None:
            beats |= {piece.beat for piece in self.partner.pieces()}  # |= adds a set
        return sorted(beats)

    def piece_columns(self):
        """The column of each of this staff's pieces, in order."""
        column_of = {beat: column for column, beat in enumerate(self.column_beats())}
        return [column_of[piece.beat] for piece in self.pieces()]

    def column_x(self, column):
        """The x position of a column (0 = first)."""
        return self.first_note_x() + column * NOTE_SPACING

    def column_for_beat(self, beat):
        """The column at this beat; for a beat with no column, the next one along."""
        # bisect_left finds where `beat` belongs in a sorted list.
        return bisect.bisect_left(self.column_beats(), beat)

    def note_columns(self):
        """For each note, the list of columns its pieces are drawn in."""
        columns = [[] for _ in self.shown.notes]  # one empty list per note
        for piece, column in zip(self.pieces(), self.piece_columns()):
            columns[piece.note_index].append(column)
        return columns

    def note_x(self, index):
        """The x position of a note's first piece (or where the next note will go)."""
        columns = self.note_columns()
        if 0 <= index < len(columns):
            return self.column_x(columns[index][0])
        end_beat = sum(note.duration for note in self.shown.notes)
        return self.column_x(self.column_for_beat(end_beat))

    def column_at(self, x):
        """Which column is at this x position, or None if none is."""
        column = round((x - self.first_note_x()) / NOTE_SPACING)
        return column if 0 <= column < len(self.column_beats()) else None

    def piece_at(self, x):
        """This staff's piece in the column at x, or None (on a grand staff a
        column may belong only to the other staff)."""
        column = self.column_at(x)
        if column is None:
            return None, None
        for piece, piece_column in zip(self.pieces(), self.piece_columns()):
            if piece_column == column:
                return piece, column
        return None, None

    def note_index_at(self, x):
        """Which note is at this x position? (Any of its pieces counts.)

        Returns the note's index, or None if there's no note there.
        """
        piece, _ = self.piece_at(x)
        return None if piece is None else piece.note_index

    def note_head_at(self, pos):
        """The index of the note whose head is under this point, or None.

        Any piece of a tied note counts. Rests don't count, since they
        can't be dragged to a new pitch.
        """
        piece, column = self.piece_at(pos.x())
        if piece is None:
            return None
        index = piece.note_index
        note = self.shown.notes[index]  # where it's *drawn*
        if note.is_rest:
            return None
        # abs() is the distance ignoring direction: abs(-3) is 3.
        close_in_x = abs(pos.x() - self.column_x(column)) <= NOTE_HEAD_WIDTH * 0.75
        close_in_y = abs(pos.y() - step_to_y(note.step)) <= NOTE_HEAD_HEIGHT * 0.75
        return index if close_in_x and close_in_y else None

    def preview_note(self, note):
        """Ask to hear this note, if Preview is switched on."""
        if self.settings.preview and not note.is_rest:
            instrument = self.part.instrument
            self.preview.emit(instrument.bank, instrument.program, self.part.sounding_pitch(note))

    def step_at(self, y):
        """The staff step for a y position; on a drum staff, the nearest drum."""
        step = y_to_step(y)
        return nearest_drum_step(step) if self.part.instrument.is_drums else step

    def mousePressEvent(self, event):
        # Qt calls this automatically whenever the mouse is clicked on us.
        self.activated.emit()
        if event.button() == Qt.RightButton:
            # Right-click deletes the note in that column, if there is one.
            index = self.note_index_at(event.position().x())
            if index is not None:  # "is not None", because index 0 is a real note
                self.remove_requested.emit(index)
            return
        if event.button() != Qt.LeftButton:
            return
        # Pressing on a note head grabs it, to drag it to a new pitch.
        index = self.note_head_at(event.position())
        if index is not None:
            self.drag_index = index
            written = self.part.notes[index]
            self.drag_start = (written.step, written.alter)  # for undo
            # Dragging keeps the note's displayed ♯/♭ and changes its line or space.
            self.drag_shown_alter = self.shown.notes[index].alter
            self.setCursor(Qt.ClosedHandCursor)
            self.preview_note(self.part.notes[index])
            return
        # Anywhere else: add a new note at the end.
        if self.settings.rest_mode:
            step = None  # a rest has no pitch, so the click's height doesn't matter
        else:
            step = self.step_at(event.position().y())
        if step is None or self.part.instrument.is_drums:
            alter = NATURAL  # rests and drums have no accidental
        elif self.settings.alter is None:
            # Follow the key: e.g. in G major an F becomes F♯.
            alter = key_alter(letter_of(step, self.part.clef), self.key)
        else:
            alter = self.settings.alter
        if step is not None:
            step, alter = self.to_written(step, alter)  # what you clicked is what's shown
        duration = self.settings.duration
        if self.settings.dotted and duration in DOTTABLE:
            duration *= 1.5  # a dotted note: 1½ times as long
        note = Note(step, duration, alter)
        self.add_requested.emit(note)
        self.preview_note(note)

    def mouseMoveEvent(self, event):
        # Qt calls this whenever the mouse moves over us (thanks to mouse tracking).
        if self.drag_index is None:
            # Not dragging: remember which note we're over, and show an open
            # hand over notes that can be grabbed.
            self.hover_index = self.note_head_at(event.position())
            self.setCursor(Qt.OpenHandCursor if self.hover_index is not None else Qt.ArrowCursor)
            if self.part.instrument.is_drums:
                # Drum staffs: say which drum is at the mouse's height.
                self.hint.emit(DRUM_MAP[self.step_at(event.position().y())].name)
            return
        # While dragging, the note follows the mouse right away, so you can see
        # and hear where it's going. The undoable edit is made on release.
        new_step = self.step_at(event.position().y())
        if new_step != self.shown.notes[self.drag_index].step:  # crossed into a new line or space
            note = self.part.notes[self.drag_index]
            note.step, note.alter = self.to_written(new_step, self.drag_shown_alter)
            self.refresh()
            self.preview_note(note)

    def leaveEvent(self, event):
        # Qt calls this when the mouse leaves the widget.
        self.hover_index = None

    def hovered_note_index(self):
        """The index of the note under the mouse, or None.

        Checked against the current notes, since an undo may have removed
        the note the mouse was last over.
        """
        if self.hover_index is not None and self.hover_index < len(self.part.notes):
            return self.hover_index
        return None

    def mouseReleaseEvent(self, event):
        # Qt calls this when a mouse button is let go: the end of a drag.
        if self.drag_index is None or event.button() != Qt.LeftButton:
            return
        index = self.drag_index
        note = self.part.notes[index]
        new = (note.step, note.alter)
        self.drag_index = None
        self.setCursor(Qt.OpenHandCursor)  # the pointer is still over the note
        if new != self.drag_start:  # only a real move becomes an undo step
            self.move_requested.emit(index, self.drag_start, new)

    def paintEvent(self, event):
        # Qt calls paintEvent automatically whenever the widget needs to be
        # drawn: when the window first opens, is resized, or uncovered.
        # We never call it ourselves.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # smooth edges
        if self.partner is None:
            painter.fillRect(self.rect(), Qt.white)    # paper background
        # (On a grand staff the GrandStaffWidget behind us paints the paper
        # and the brace; we leave our background see-through.)

        pieces = self.pieces()

        # The cursor goes first, so the staff and notes are drawn on top of it.
        # It covers every column of the playing note (all its tied pieces).
        columns = self.note_columns()
        if self.playing_index is not None and self.playing_index < len(columns):
            left = self.column_x(columns[self.playing_index][0]) - NOTE_SPACING / 2
            right = self.column_x(columns[self.playing_index][-1]) + NOTE_SPACING / 2
            top = step_to_y(HIGHEST_STEP + 2)
            bottom = step_to_y(LOWEST_STEP - 2)
            painter.fillRect(QRectF(left, top, right - left, bottom - top), CURSOR_COLOR)

        painter.setPen(QPen(self.ink, 1))

        right_edge = self.width() - MARGIN
        for step in range(0, TOP_LINE_STEP + 1, 2):  # steps 0, 2, 4, 6, 8
            y = step_to_y(step)
            painter.drawLine(QPointF(MARGIN, y), QPointF(right_edge, y))
        self.draw_clef(painter)
        self.draw_key_signature(painter)
        self.draw_time_signature(painter)

        # Draw every piece. The whole picture is redrawn from self.part each
        # time, so the model is the "truth" and the picture just shows it.
        # The model decides how notes are split and tied (pieces) and which
        # ♯ ♭ ♮ signs are needed (accidental_signs).
        # enumerate gives each item along with its position: (0, first), (1, second), ...
        signs = self.shown.accidental_signs(self.key, self.measure_beats)
        piece_columns = self.piece_columns()
        bar_lines = []
        for i, piece in enumerate(pieces):
            note = self.shown.notes[piece.note_index]
            x = self.column_x(piece_columns[i])
            self.draw_note(painter, x, note, piece.duration)
            if piece.first and signs[piece.note_index] is not None:
                self.draw_accidental(painter, x, note.step, signs[piece.note_index])  # only once per note
            if piece.tied:
                self.draw_tie(painter, x, self.column_x(piece_columns[i + 1]), note.step)
            if piece.ends_measure:
                # Halfway between the last column of this measure and the first
                # of the next, so bar lines line up on both staves of a grand staff.
                next_column = self.column_for_beat(piece.beat + piece.duration)
                bar_lines.append(self.column_x(next_column) - NOTE_SPACING / 2)

        painter.setPen(QPen(self.ink, 1))
        for x in bar_lines:
            painter.drawLine(QPointF(x, step_to_y(TOP_LINE_STEP)), QPointF(x, step_to_y(0)))

    def clef_layout(self):
        """Work out the clef's font, where to draw it, and where it ends.

        Returns (font, position, right edge). Both drawing the clef and
        placing the key signature after it use this, so they always agree.
        """
        if self.part.instrument.is_drums:
            # The drum clef is drawn as shapes, not a font symbol (see draw_clef).
            return None, None, MARGIN + 8 + DRUM_CLEF_WIDTH
        clef = self.part.clef
        symbol = CLEF_SYMBOLS[clef]
        top = step_to_y(CLEF_TOP_STEP[clef])
        bottom = step_to_y(CLEF_BOTTOM_STEP[clef])

        # Measure the symbol at a test size, then scale the font so its exact
        # outline (its "tight bounding rectangle") is as tall as we want.
        font = QFont(CLEF_FONT)
        font.setPixelSize(100)
        test_height = QFontMetricsF(font).tightBoundingRect(symbol).height()
        font.setPixelSize(round(100 * (bottom - top) / test_height))
        outline = QFontMetricsF(font).tightBoundingRect(symbol)

        # drawText places the text's *baseline* (the line letters sit on).
        # outline.top() is how far the symbol reaches above its baseline
        # (a negative number), so this puts the symbol's top exactly at `top`.
        left = MARGIN + 8
        position = QPointF(left - outline.left(), top - outline.top())
        return font, position, left + outline.width()

    def draw_clef(self, painter):
        """Draw the part's clef symbol at the start of the staff."""
        if self.part.instrument.is_drums:
            # The percussion clef: two thick bars across the middle of the staff.
            top, bottom = step_to_y(6), step_to_y(2)
            bar = DRUM_CLEF_WIDTH * 0.35
            left = MARGIN + 8
            painter.fillRect(QRectF(left, top, bar, bottom - top), self.ink)
            painter.fillRect(QRectF(left + DRUM_CLEF_WIDTH - bar, top, bar, bottom - top), self.ink)
            return
        font, position, _ = self.clef_layout()
        painter.setFont(font)
        painter.drawText(position, CLEF_SYMBOLS[self.part.clef])

    def key_signature_right(self):
        """Where the key signature ends (just after the clef if there's none)."""
        _, _, clef_right = self.clef_layout()
        return clef_right + KEY_GAP + abs(self.key) * KEY_SIGN_SPACING

    def draw_accidental(self, painter, x, step, alter):
        """Draw a ♯, ♭ or ♮ just left of the note head at (x, step)."""
        self.draw_sign(painter, x - NOTE_HEAD_WIDTH / 2 - 2, step, alter)  # a small gap

    def draw_key_signature(self, painter):
        """Draw the key's sharps or flats after the clef, in their standard places."""
        if self.key == 0:
            return  # C major (and every drum staff): nothing to draw
        if self.key > 0:
            steps, alter = KEY_SHARP_STEPS[self.part.clef][:self.key], SHARP
        else:
            steps, alter = KEY_FLAT_STEPS[self.part.clef][:-self.key], FLAT
        _, _, clef_right = self.clef_layout()
        for i, step in enumerate(steps):
            # Each sign's right edge, one KEY_SIGN_SPACING further along.
            self.draw_sign(painter, clef_right + KEY_GAP + (i + 1) * KEY_SIGN_SPACING, step, alter)

    def draw_sign(self, painter, right, step, alter):
        """Draw a ♯, ♭ or ♮ on a staff step, with its right edge at x = right."""
        symbol = ACCIDENTAL_SYMBOLS[alter]
        # Measure at a test size, then scale to the height we want (like draw_clef).
        font = QFont(CLEF_FONT)
        font.setPixelSize(100)
        test_height = QFontMetricsF(font).tightBoundingRect(symbol).height()
        font.setPixelSize(round(100 * ACCIDENTAL_HEIGHT[alter] * LINE_SPACING / test_height))
        outline = QFontMetricsF(font).tightBoundingRect(symbol)  # the symbol's exact shape
        y = step_to_y(step)
        if alter == FLAT:
            # A flat's round bowl sits on the note's line or space, so its
            # bottom goes just below the note's center.
            baseline = y + LINE_SPACING * 0.5 - outline.bottom()
        else:
            # Sharps and naturals are centered on the note.
            baseline = y - (outline.top() + outline.height() / 2)
        painter.setFont(font)
        painter.setPen(QPen(self.ink, 1))
        painter.drawText(QPointF(right - outline.right(), baseline), symbol)

    def draw_tie(self, painter, x1, x2, step):
        """Draw a tie: a thin curved band from the note head at x1 to the one at x2.

        Ties curve away from the stems: below the notes when stems go up,
        above when they go down.
        """
        direction = 1 if step < MIDDLE_LINE_STEP else -1  # +1 = curve downward (y grows down)
        y = step_to_y(step) + direction * NOTE_HEAD_HEIGHT * 0.6
        start = QPointF(x1 + NOTE_HEAD_WIDTH * 0.3, y)
        end = QPointF(x2 - NOTE_HEAD_WIDTH * 0.3, y)
        middle_x = (x1 + x2) / 2
        # Two curves between the same ends, one bulging further than the
        # other; filling between them gives a tie that's thick in the middle
        # and thin at the ends, like a printed one.
        path = QPainterPath(start)
        path.quadTo(QPointF(middle_x, y + direction * LINE_SPACING * 0.9), end)
        path.quadTo(QPointF(middle_x, y + direction * LINE_SPACING * 0.65), start)
        painter.setPen(QPen(self.ink, 0.8))
        painter.setBrush(self.ink)
        painter.drawPath(path)

    def draw_dot(self, painter, x, step):
        """A rhythm dot (it makes a note 1½ times as long)."""
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.ink)
        radius = LINE_SPACING * 0.15
        painter.drawEllipse(QPointF(x, step_to_y(step)), radius, radius)

    def draw_note(self, painter, x, note, duration):
        """Draw a note (or one piece of it) at x, shaped by `duration`.

        `duration` is passed separately because a tied note's pieces can be
        shorter than the note itself.
        """
        # A dotted value is drawn as the plain value plus a dot after it.
        duration, dotted = undotted(duration)
        if note.is_rest:
            self.draw_rest(painter, x, duration)
            if dotted:
                self.draw_dot(painter, x + LINE_SPACING * 0.8, 5)  # in the third space
            return

        y = step_to_y(note.step)
        self.draw_ledger_lines(painter, x, note.step)
        if dotted:
            # The dot goes in a space: a note on a line gets its dot just above.
            dot_step = note.step if note.step % 2 else note.step + 1
            self.draw_dot(painter, x + NOTE_HEAD_WIDTH / 2 + 5, dot_step)

        is_cymbal = (self.part.instrument.is_drums
                     and DRUM_MAP[nearest_drum_step(note.step)].cymbal)
        if is_cymbal:
            # Cymbals on a drum staff get an x-shaped head instead of an oval.
            half_w, half_h = NOTE_HEAD_WIDTH * 0.4, NOTE_HEAD_HEIGHT * 0.45
            painter.setPen(QPen(self.ink, 1.8))
            painter.drawLine(QPointF(x - half_w, y - half_h), QPointF(x + half_w, y + half_h))
            painter.drawLine(QPointF(x - half_w, y + half_h), QPointF(x + half_w, y - half_h))
        else:
            # Note head: whole and half notes are hollow; shorter notes are filled.
            # The pen draws outlines; the brush fills the inside.
            if duration >= HALF:
                painter.setPen(QPen(self.ink, 1.8))  # thicker outline for hollow heads
                painter.setBrush(Qt.NoBrush)
            else:
                painter.setPen(QPen(self.ink, 1))
                painter.setBrush(self.ink)
            painter.drawEllipse(QPointF(x, y), NOTE_HEAD_WIDTH / 2, NOTE_HEAD_HEIGHT / 2)
        painter.setPen(QPen(self.ink, 1))

        if duration == WHOLE:
            return  # whole notes have no stem

        # Notation rule: notes below the middle line have stems going up on
        # the right; notes on or above it have stems going down on the left.
        if note.step < MIDDLE_LINE_STEP:
            stem_x = x + NOTE_HEAD_WIDTH / 2 - 0.5
            stem_end_y = y - STEM_LENGTH
        else:
            stem_x = x - NOTE_HEAD_WIDTH / 2 + 0.5
            stem_end_y = y + STEM_LENGTH
        painter.drawLine(QPointF(stem_x, y), QPointF(stem_x, stem_end_y))

        if duration == EIGHTH:
            self.draw_flag(painter, stem_x, stem_end_y, stem_up=note.step < MIDDLE_LINE_STEP)

    def draw_flag(self, painter, stem_x, stem_end_y, stem_up):
        """Draw an eighth-note flag: a curve from the end of the stem, to the right."""
        # The flag curls back toward the note head: down for an up-stem,
        # up for a down-stem. direction flips the curve's y offsets.
        direction = 1 if stem_up else -1
        s = LINE_SPACING
        path = QPainterPath(QPointF(stem_x, stem_end_y))
        # A cubic curve: two "pull" points that bend it, then the end point.
        path.cubicTo(
            QPointF(stem_x + s * 0.1, stem_end_y + direction * s * 0.9),
            QPointF(stem_x + s * 1.1, stem_end_y + direction * s * 1.1),
            QPointF(stem_x + s * 0.7, stem_end_y + direction * s * 2.2),
        )
        painter.setPen(QPen(self.ink, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setPen(QPen(self.ink, 1))

    def draw_rest(self, painter, x, duration):
        """Draw the rest symbol for this duration, centered at horizontal position x.

        Rests sit at fixed heights on the staff. Positions are given in staff
        steps (halves like 5.5 are allowed) so they scale with LINE_SPACING.
        """
        s = LINE_SPACING
        if duration == WHOLE:
            # A block hanging down from the 4th line (step 6).
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.ink)
            painter.drawRect(QRectF(x - s * 0.5, step_to_y(6), s, s * 0.5))
        elif duration == HALF:
            # A block sitting on top of the middle line (step 4).
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.ink)
            painter.drawRect(QRectF(x - s * 0.5, step_to_y(4) - s * 0.5, s, s * 0.5))
        elif duration == QUARTER:
            # A thick zig-zag with a small hook at the bottom.
            path = QPainterPath(QPointF(x - s * 0.15, step_to_y(7)))
            path.lineTo(x + s * 0.3, step_to_y(5.5))
            path.lineTo(x - s * 0.25, step_to_y(4))
            path.lineTo(x + s * 0.25, step_to_y(2.5))
            path.quadTo(QPointF(x - s * 0.55, step_to_y(2.4)), QPointF(x + s * 0.05, step_to_y(1)))
            painter.setPen(QPen(self.ink, s * 0.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        elif duration == EIGHTH:
            # A dot, a small curl to the right, then a slanted stroke down-left.
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.ink)
            painter.drawEllipse(QPointF(x - s * 0.25, step_to_y(5)), s * 0.18, s * 0.18)
            path = QPainterPath(QPointF(x - s * 0.25, step_to_y(4.7)))
            path.quadTo(QPointF(x + s * 0.1, step_to_y(4.5)), QPointF(x + s * 0.35, step_to_y(5.3)))
            path.lineTo(x - s * 0.05, step_to_y(2))
            painter.setPen(QPen(self.ink, 1.6))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        painter.setPen(QPen(self.ink, 1))  # put the normal pen back for whatever is drawn next

    def draw_ledger_lines(self, painter, x, step):
        """Draw short extra lines for notes above or below the staff."""
        half_width = NOTE_HEAD_WIDTH * 0.8
        # Below the staff: a ledger line at every even step from -2 down to the note.
        for ledger_step in range(-2, step - 1, -2):
            y = step_to_y(ledger_step)
            painter.drawLine(QPointF(x - half_width, y), QPointF(x + half_width, y))
        # Above the staff: from step 10 up to the note.
        for ledger_step in range(TOP_LINE_STEP + 2, step + 1, 2):
            y = step_to_y(ledger_step)
            painter.drawLine(QPointF(x - half_width, y), QPointF(x + half_width, y))


class GrandStaffWidget(QWidget):
    """Two staves stacked (right hand above, left hand below), joined at the
    left by a brace and a line, as piano music is written.

    The two StaffWidgets do the real work; this widget arranges them and
    paints what belongs to both: the paper behind them and the brace.
    """

    def __init__(self, upper, lower):
        super().__init__()
        self.upper = upper
        self.lower = lower
        upper.partner = lower  # partners share their columns, so notes line up
        lower.partner = upper
        layout = QVBoxLayout(self)  # a layout that stacks widgets top to bottom
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(upper)
        layout.addWidget(lower)

    def staves(self):
        return [self.upper, self.lower]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.white)  # paper (the staves are see-through)
        # From the upper staff's top line to the lower staff's bottom line.
        # Each staff's own y position inside this widget is added on.
        top = self.upper.y() + step_to_y(TOP_LINE_STEP)
        bottom = self.lower.y() + step_to_y(0)
        painter.setPen(QPen(self.upper.ink, 1.5))
        painter.drawLine(QPointF(MARGIN, top), QPointF(MARGIN, bottom))  # the line joining the staves
        self.draw_brace(painter, top, bottom)

    def draw_brace(self, painter, top, bottom):
        """The curly brace, drawn as a filled shape just left of the staves.

        It's two curves, mirror images above and below the middle, each
        made of a thick and a thin edge so it tapers like a printed brace.
        """
        right = MARGIN - 4
        width = LINE_SPACING * 1.3
        middle = (top + bottom) / 2
        path = QPainterPath(QPointF(right, top))
        # Outer edge, top half: out to the left, then into the point at the middle.
        path.cubicTo(QPointF(right - width, top + (middle - top) * 0.1),
                     QPointF(right, middle - (middle - top) * 0.25),
                     QPointF(right - width, middle))
        # Outer edge, bottom half (the mirror image).
        path.cubicTo(QPointF(right, middle + (bottom - middle) * 0.25),
                     QPointF(right - width, bottom - (bottom - middle) * 0.1),
                     QPointF(right, bottom))
        # Back up along a slightly thinner inner edge, closing the shape.
        inset = width * 0.25
        path.cubicTo(QPointF(right - width + inset, bottom - (bottom - middle) * 0.1),
                     QPointF(right + inset * 0.5, middle + (bottom - middle) * 0.25),
                     QPointF(right - width, middle))
        path.cubicTo(QPointF(right + inset * 0.5, middle - (middle - top) * 0.25),
                     QPointF(right - width + inset, top + (middle - top) * 0.1),
                     QPointF(right, top))
        painter.setPen(QPen(self.upper.ink, 0.8))
        painter.setBrush(self.upper.ink)
        painter.drawPath(path)


class MainWindow(QMainWindow):
    """The application window: toolbars on top, one tab per instrument below.

    QMainWindow already has places for toolbars, menus, and a status bar;
    we fill them in.
    """

    def __init__(self):
        super().__init__()

        # The player comes first: every tab's staff connects to it as it's made.
        self.player = Player()
        self.file_path = None           # where the score was last saved; None = never saved
        self.score = Score()            # all the music: one Part per tab
        self.settings = EditSettings()  # shared by every tab's staff
        # View setting: show transposing parts at sounding (concert) pitch.
        self.concert_pitch = False
        # The staff last clicked: Backspace acts on it (matters on a grand staff).
        self.active_staff = None

        # Every edit goes onto this stack as a command (see edits.py), so it
        # can be undone. The stack also knows whether we're back at the last
        # saved state ("clean"), which is what the title bar's * shows.
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self.update_title)

        # The tabs. Tab number i always shows score.parts[i]: tabs can't be
        # dragged into a new order, so the two lists stay lined up.
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)  # an x on each tab
        self.tabs.tabCloseRequested.connect(self.on_close_tab)
        self.setCentralWidget(self.tabs)

        # The "+ Instrument" button, in the corner beside the tabs. Clicking it
        # opens a menu with one entry per instrument.
        instrument_menu = QMenu(self)
        self.fill_instrument_menu(instrument_menu)
        instrument_menu.triggered.connect(self.on_add_instrument)
        add_button = QToolButton()
        add_button.setText("+ Instrument")
        add_button.setMenu(instrument_menu)
        add_button.setPopupMode(QToolButton.InstantPopup)  # open the menu on click
        self.tabs.setCornerWidget(add_button, Qt.TopRightCorner)

        # Right-clicking a tab opens a menu to change its instrument.
        # CustomContextMenu means "tell us about right-clicks, we'll show the menu".
        tab_bar = self.tabs.tabBar()
        tab_bar.setContextMenuPolicy(Qt.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self.on_tab_right_click)

        self.add_tab(GRAND_PIANO)  # every score starts with a piano, on a grand staff

        toolbar = self.addToolBar("Editing")
        # A QActionGroup makes its buttons work like radio buttons:
        # checking one automatically unchecks the others.
        self.duration_group = QActionGroup(self)
        for label, duration, shortcut in DURATION_CHOICES:
            action = QAction(f"{label} ({shortcut})", self)
            action.setCheckable(True)        # stays pressed in when chosen
            action.setShortcut(shortcut)     # pressing the key = clicking the button
            action.setData(duration)         # remember which duration this button means
            action.setChecked(duration == self.settings.duration)
            self.duration_group.addAction(action)
            toolbar.addAction(action)

        # Signals and slots: when any button in the group is triggered (clicked
        # or chosen by its shortcut), Qt calls our method with that button.
        # "connect" is how we say "when this happens, call that."
        self.duration_group.triggered.connect(self.on_duration_chosen)

        # The dot: makes the next half or quarter notes 1½ times as long.
        self.dot_action = QAction("Dot (.)", self)
        self.dot_action.setToolTip("Dotted notes: 1½ times as long (half and quarter notes)")
        self.dot_action.setCheckable(True)
        self.dot_action.setShortcut(".")
        self.dot_action.toggled.connect(self.on_dot_toggled)
        toolbar.addAction(self.dot_action)

        # The Rest button is a separate on/off switch, not part of the group,
        # so it combines with whichever duration is chosen.
        toolbar.addSeparator()  # a small divider line in the toolbar
        self.rest_action = QAction("Rest (R)", self)
        self.rest_action.setCheckable(True)
        self.rest_action.setShortcut("R")
        # toggled is a different signal: it sends True when switched on, False when off.
        self.rest_action.toggled.connect(self.on_rest_toggled)
        toolbar.addAction(self.rest_action)

        # Sharp / flat / natural for new notes: radio buttons, like the durations.
        toolbar.addSeparator()
        self.accidental_group = QActionGroup(self)
        for text, tip, alter, shortcut in ACCIDENTAL_CHOICES:
            action = QAction(f"{text} ({shortcut})", self)  # e.g. "♯ (S)"
            action.setToolTip(f"{tip} ({shortcut}): for the next notes you place")
            action.setCheckable(True)
            action.setShortcut(shortcut)
            action.setData(alter)
            action.setChecked(alter == self.settings.alter)
            self.accidental_group.addAction(action)
            toolbar.addAction(action)
        self.accidental_group.triggered.connect(self.on_accidental_chosen)

        toolbar.addSeparator()
        self.delete_last_action = QAction("Delete Last", self)
        self.delete_last_action.setToolTip("Delete the last note (Backspace)")
        self.delete_last_action.setShortcut("Backspace")
        self.delete_last_action.triggered.connect(self.on_delete_last)
        toolbar.addAction(self.delete_last_action)

        toolbar.addSeparator()
        self.preview_action = QAction("Preview", self)
        self.preview_action.setToolTip("Hear each note as you place it")
        self.preview_action.setCheckable(True)
        self.preview_action.setChecked(self.settings.preview)
        self.preview_action.toggled.connect(self.on_preview_toggled)
        toolbar.addAction(self.preview_action)

        # Transport controls: the buttons that control playback. They get
        # their own toolbar, on a second row (one long row didn't fit).
        self.addToolBarBreak()  # start a new row of toolbars
        toolbar = self.addToolBar("Playback")
        self.play_action = QAction("Play", self)
        self.play_action.triggered.connect(self.on_play)
        toolbar.addAction(self.play_action)
        # The label switches between "Play" and "Resume". Make the button wide
        # enough for the longer word, or Qt shortens it to "R...e".
        toolbar.widgetForAction(self.play_action).setMinimumWidth(60)

        self.pause_action = QAction("Pause", self)
        self.pause_action.triggered.connect(self.player.pause)
        toolbar.addAction(self.pause_action)

        self.stop_action = QAction("Stop (Esc)", self)
        self.stop_action.setShortcut("Escape")
        self.stop_action.triggered.connect(self.player.stop)
        toolbar.addAction(self.stop_action)

        # Space switches between play and pause. This action isn't a toolbar
        # button; adding it to the window just makes its shortcut work.
        self.play_pause_action = QAction("Play/Pause", self)
        self.play_pause_action.setShortcut("Space")
        self.play_pause_action.triggered.connect(self.on_play_pause)
        self.addAction(self.play_pause_action)

        # Tempo: a slider plus a label showing its value.
        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Tempo "))  # toolbars can hold any widget, not just buttons
        self.tempo_slider = QSlider(Qt.Horizontal)
        self.tempo_slider.setRange(MIN_TEMPO, MAX_TEMPO)
        self.tempo_slider.setValue(self.score.tempo_bpm)
        self.tempo_slider.setFixedWidth(150)
        self.tempo_slider.setFocusPolicy(Qt.NoFocus)  # keep Space for play/pause
        toolbar.addWidget(self.tempo_slider)
        self.tempo_label = QLabel()
        toolbar.addWidget(self.tempo_label)
        # valueChanged sends the slider's new number every time it moves.
        self.tempo_slider.valueChanged.connect(self.on_tempo_changed)
        self.on_tempo_changed(self.tempo_slider.value())  # show the starting value

        # A third row for settings of the whole piece: key, time, and how it's shown.
        self.addToolBarBreak()
        toolbar = self.addToolBar("Score")

        # Key signature: a drop-down list of all 15 keys, 7 flats to 7 sharps.
        toolbar.addWidget(QLabel(" Key "))
        self.key_box = QComboBox()
        for key in sorted(KEY_NAMES):  # sorted: -7, -6, ... 0 ... 7
            self.key_box.addItem(key_name(key), key)  # (text shown, value kept with it)
        self.key_box.setCurrentIndex(self.key_box.findData(self.score.key))
        self.key_box.setFocusPolicy(Qt.NoFocus)  # keep Space for play/pause
        self.key_box.currentIndexChanged.connect(self.on_key_chosen)
        toolbar.addWidget(self.key_box)

        # Time signature: the common ones, e.g. "3/4", "6/8".
        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Time "))
        self.time_box = QComboBox()
        # Entry i of the box is TIME_SIGNATURES[i]. (Storing the tuple itself
        # with addItem doesn't work: Qt converts it, and findData can't match it.)
        for top, bottom in TIME_SIGNATURES:
            self.time_box.addItem(f"{top}/{bottom}")
        self.time_box.setCurrentIndex(TIME_SIGNATURES.index(self.score.time_signature))
        self.time_box.setFocusPolicy(Qt.NoFocus)  # keep Space for play/pause
        self.time_box.currentIndexChanged.connect(self.on_time_signature_chosen)
        toolbar.addWidget(self.time_box)

        # Concert pitch: a view switch, shared by this toolbar and the View menu.
        toolbar.addSeparator()
        self.concert_action = QAction("Concert Pitch", self)
        self.concert_action.setToolTip(
            "Show transposing instruments at the pitch they sound (not what their players read)")
        self.concert_action.setCheckable(True)
        self.concert_action.toggled.connect(self.on_concert_pitch_toggled)
        toolbar.addAction(self.concert_action)

        # Keep the buttons and the cursor in step with the player.
        self.player.state_changed.connect(self.update_transport_buttons)
        self.player.note_started.connect(self.on_note_started)
        self.update_transport_buttons(self.player.state)

        self.build_file_menu()
        self.build_edit_menu()
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.concert_action)  # the same action as the toolbar button
        self.update_title()

    # --- Tabs ---------------------------------------------------------------

    def staves_in_tab(self, index):
        """The staff (or, on a grand staff, both staves) in tab number `index`.

        Each tab holds a scroll area; QScrollArea.widget() gives back what's
        inside: a StaffWidget, or a GrandStaffWidget holding two.
        """
        area = self.tabs.widget(index)
        if area is None:
            return []
        inside = area.widget()
        # isinstance checks what kind of object something is.
        return inside.staves() if isinstance(inside, GrandStaffWidget) else [inside]

    def staff_at(self, index):
        """The (upper) staff in tab number `index`, or None if there's no such tab."""
        staves = self.staves_in_tab(index)
        return staves[0] if staves else None

    def current_staff(self):
        """The staff being worked on: in the open tab, the one last clicked."""
        staves = self.staves_in_tab(self.tabs.currentIndex())
        return self.active_staff if self.active_staff in staves else staves[0]

    def set_active_staff(self, staff):
        """Slot: a staff was clicked; Backspace and similar now act on it."""
        self.active_staff = staff

    def add_tab(self, instrument):
        """Add a part for this instrument to the score, with a tab to show it."""
        part = self.score.add_part(instrument)
        self.show_part(part)

    def make_staff(self, part):
        """A StaffWidget for one staff, wired up to the player and the undo stack.

        `part` is the Part this staff shows: a tab's part, or on a grand staff
        possibly its lower staff (part.lower). Edits go to exactly that Part.
        """
        staff = StaffWidget(part, self.settings)
        staff.preview.connect(self.player.preview)  # the signal's (bank, program, pitch) go straight through
        staff.hint.connect(lambda text: self.statusBar().showMessage(text, 2000))
        staff.activated.connect(lambda staff=staff: self.set_active_staff(staff))
        # Turn the staff's requests into undoable commands. "part=part" stores
        # this staff's part inside each lambda (see make_mute_solo).
        staff.add_requested.connect(
            lambda note, part=part: self.undo_stack.push(AddNote(self, part, note)))
        staff.remove_requested.connect(
            lambda i, part=part: self.undo_stack.push(RemoveNote(self, part, i)))
        staff.move_requested.connect(
            lambda i, old, new, part=part: self.undo_stack.push(
                SetNotePitch(self, part, i, old, new, "Move note")))
        return staff

    def show_part(self, part, index=None):
        """Make a tab for a part that's already in the score.

        The tab goes at position `index`, or at the end if index is None.
        A grand-staff part gets two staves joined by a brace.
        """
        staves = [self.make_staff(staff_part) for staff_part in part.staves()]
        if len(staves) == 2:
            inside = GrandStaffWidget(*staves)  # * spreads the list into two arguments
        else:
            inside = staves[0]
        for staff in staves:
            self.update_staff_display(staff)  # written or concert pitch, and the right key

        # Put the staff(s) in a scroll area, so long pieces can scroll sideways.
        area = QScrollArea()
        area.setWidget(inside)
        area.setWidgetResizable(True)  # stretch the staff to fill the window when it's short
        area.setFocusPolicy(Qt.NoFocus)  # keep Space for play/pause
        for staff in staves:
            staff.scroll_to.connect(lambda x, area=area: self.scroll_into_view(area, x))

        label = self.unused_tab_label(part.instrument.name)
        if index is None:
            index = self.tabs.addTab(area, label)
        else:
            self.tabs.insertTab(index, area, label)
        self.tabs.tabBar().setTabButton(index, QTabBar.LeftSide, self.make_mute_solo(part))
        self.tabs.setCurrentIndex(index)  # switch to the new tab
        self.refresh_audibility()  # a new part may be silent if another tab is soloed

    def make_mute_solo(self, part):
        """Build the small M / S buttons that sit on the left side of a tab."""
        mute = QToolButton()
        mute.setText("M")
        mute.setToolTip("Mute: silence this instrument")  # shown when the mouse hovers
        mute.setObjectName("mute")  # the name the style sheet's #mute refers to
        solo = QToolButton()
        solo.setText("S")
        solo.setToolTip("Solo: play only the soloed instruments")
        solo.setObjectName("solo")
        for button in (mute, solo):
            button.setCheckable(True)
            button.setFocusPolicy(Qt.NoFocus)  # keep Space for play/pause
        # Start out matching the part (a tab brought back by undo keeps its Mute/Solo).
        mute.setChecked(part.muted)
        solo.setChecked(part.soloed)

        # Each button needs to know which part it controls. A lambda is a
        # tiny function written in place; "part=part" stores this tab's part
        # inside it, so every tab's buttons control their own part.
        mute.toggled.connect(lambda checked, part=part: self.set_mute(part, checked))
        solo.toggled.connect(lambda checked, part=part: self.set_solo(part, checked))

        # A small container widget holding the two buttons side by side.
        box = QWidget()
        box.setStyleSheet(MUTE_SOLO_STYLE)
        layout = QHBoxLayout(box)  # a layout arranges widgets in a row
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(mute)
        layout.addWidget(solo)
        return box

    def set_mute(self, part, muted):
        part.muted = muted
        self.player.apply_mutes()
        self.refresh_audibility()

    def set_solo(self, part, soloed):
        part.soloed = soloed
        self.player.apply_mutes()
        self.refresh_audibility()

    def refresh_audibility(self):
        """Gray out every staff that Mute/Solo has silenced."""
        for index in range(self.tabs.count()):
            for staff in self.staves_in_tab(index):  # both staves of a grand staff
                staff.set_dimmed(not self.score.is_audible(index))

    def unused_tab_label(self, name):
        """A tab label not already in use: "Violin", else "Violin 2", "Violin 3", ..."""
        labels = {self.tabs.tabText(i) for i in range(self.tabs.count())}  # a set
        label = name
        number = 1
        while label in labels:  # keep trying until we find a free label
            number += 1
            label = f"{name} {number}"
        return label

    def all_staffs(self):
        """Every staff in every tab, in order (a grand staff contributes two)."""
        return [staff for i in range(self.tabs.count()) for staff in self.staves_in_tab(i)]

    def tab_of_part(self, part):
        """The tab number showing this Part (a tab's part or a lower staff), or None."""
        for index in range(self.tabs.count()):
            for staff in self.staves_in_tab(index):
                if staff.part is part:  # "is": this exact Part object
                    return index
        return None

    def scroll_into_view(self, area, x):
        """Scroll a tab's scroll area so position x on its staff is visible."""
        # The staff may have just grown, and Qt only updates the scroll bar's
        # range a moment later. A 0 ms single-shot timer runs our code as
        # soon as Qt has finished what it's doing: "do this next".
        QTimer.singleShot(0, lambda: area.ensureVisible(round(x), 0, 3 * NOTE_SPACING, 0))

    def on_add_instrument(self, action):
        """Slot: an instrument was chosen from the "+ Instrument" menu."""
        if len(self.score.parts) >= MAX_PARTS:
            # The status bar is the strip along the bottom of the window.
            self.statusBar().showMessage(f"At most {MAX_PARTS} instruments.", 3000)
            return
        self.undo_stack.push(AddPart(self, self.score, action.data()))

    def fill_instrument_menu(self, menu, current=None, allowed=None):
        """Add one entry per instrument to a menu, under group headings.

        If `current` is given, that instrument's entry gets a check mark.
        If `allowed` is given (a function), instruments it says no to are grayed out.
        """
        for heading, instruments in INSTRUMENT_GROUPS:
            menu.addSection(heading)  # a labeled divider
            for instrument in instruments:
                action = self.add_instrument_entry(menu, instrument, current)
                if allowed is not None:
                    action.setEnabled(allowed(instrument))

    def add_instrument_entry(self, menu, instrument, current):
        """One instrument's entry in an instrument menu."""
        clef = "grand staff" if instrument.grand else instrument.clef
        label = instrument.name if instrument.grand else f"{instrument.name}  ({clef})"
        action = menu.addAction(label)
        action.setData(instrument)  # remember which instrument this entry means
        if current is not None:
            action.setCheckable(True)
            action.setChecked(instrument == current)
        return action

    def on_tab_right_click(self, pos):
        """Slot: a tab was right-clicked. Offer to change its instrument."""
        index = self.tabs.tabBar().tabAt(pos)  # which tab is at that point (-1: none)
        if index < 0:
            return
        part = self.score.parts[index]
        menu = QMenu(self)
        if part.instrument.grand:
            # A grand staff holds two hands; one-staff instruments can't.
            menu.addSection("Change instrument (grand staff: keyboards only)")
        else:
            menu.addSection("Change instrument")  # a heading at the top of the menu
        # Grand staff <-> grand staff, one staff <-> one staff.
        same_kind = lambda instrument: instrument.grand == part.instrument.grand
        self.fill_instrument_menu(menu, current=part.instrument, allowed=same_kind)
        # exec() shows the menu where the mouse is and waits for a choice.
        # It returns the chosen action, or None if the menu was dismissed.
        chosen = menu.exec(self.tabs.tabBar().mapToGlobal(pos))
        if chosen is not None and chosen.data() != part.instrument:
            self.undo_stack.push(ChangeInstrument(self, part, chosen.data()))

    def on_close_tab(self, index):
        """Slot: the x on a tab was clicked."""
        if self.tabs.count() == 1:
            self.statusBar().showMessage("A score needs at least one instrument.", 3000)
            return
        self.undo_stack.push(RemovePart(self, self.score, index))

    # --- What the undoable commands call (the "view" in edits.py) -------------

    def part_changed(self, part, index):
        """A part's notes changed: show its tab, redraw it, and show note `index`.

        `part` may be a grand staff's lower staff; its own StaffWidget is found.
        """
        tab_index = self.tab_of_part(part)
        if tab_index is None:
            return
        self.tabs.setCurrentIndex(tab_index)  # undo shows you what it undid
        for staff in self.staves_in_tab(tab_index):
            if staff.part is part:
                staff.refresh()
                staff.scroll_to.emit(staff.note_x(max(index, 0)))

    def instrument_changed(self, part):
        """A part switched instruments: relabel its tab and redraw (the clef may differ)."""
        self.stop_if_playing()  # the player picked the old instrument when it started
        tab_index = self.tab_of_part(part)
        if tab_index is None:
            return
        self.tabs.setTabText(tab_index, "")  # so its own old name doesn't count as taken
        self.tabs.setTabText(tab_index, self.unused_tab_label(part.instrument.name))
        self.tabs.setCurrentIndex(tab_index)
        for staff in self.staves_in_tab(tab_index):
            self.update_staff_display(staff)  # a transposing instrument shows another key

    def insert_part(self, index, part):
        """Add a part to the score with its own tab, at position `index`."""
        self.stop_if_playing()
        self.score.insert_part(index, part)
        self.show_part(part, index)

    def remove_part_at(self, index):
        """Remove the part (and its tab) at position `index`."""
        self.stop_if_playing()
        area = self.tabs.widget(index)
        self.tabs.removeTab(index)
        self.score.remove_part(index)  # keep the score lined up with the tabs
        area.deleteLater()  # free the scroll area (and the staff inside it)
        self.refresh_audibility()  # closing a soloed tab un-silences the others

    def set_key(self, key):
        """Change the key signature, the Key drop-down, and every staff."""
        self.score.key = key  # first, so on_key_chosen sees no new edit
        self.key_box.setCurrentIndex(self.key_box.findData(key))
        for staff in self.all_staffs():
            self.update_staff_display(staff)  # transposing parts show their own key

    def set_tempo(self, bpm):
        """Change the tempo and move the slider to match."""
        self.score.tempo_bpm = bpm  # set this first, so on_tempo_changed sees no edit
        self.tempo_slider.setValue(bpm)

    def stop_if_playing(self):
        # Adding or removing a part renumbers the ones after it, which would
        # mix up the player's part numbers. Stopping first keeps things simple.
        if self.player.state != STOPPED:
            self.player.stop()

    # --- Editing ------------------------------------------------------------

    def on_duration_chosen(self, action):
        """Slot: called by Qt when a duration button is chosen."""
        self.settings.duration = action.data()
        # Only half and quarter notes can be dotted; gray out Dot for the others.
        self.dot_action.setEnabled(action.data() in DOTTABLE)

    def on_dot_toggled(self, checked):
        """Slot: the Dot button was switched on or off."""
        self.settings.dotted = checked

    def on_accidental_chosen(self, action):
        """Slot: ♮, ♯ or ♭ was chosen for the next notes."""
        self.settings.alter = action.data()

    def on_rest_toggled(self, checked):
        """Slot: called by Qt when the Rest button is switched on or off."""
        self.settings.rest_mode = checked

    def on_preview_toggled(self, checked):
        """Slot: the Preview button was switched on or off."""
        self.settings.preview = checked

    def on_delete_last(self):
        """Slot: delete the last note in the open tab."""
        part = self.current_staff().part
        if part.notes:  # nothing to do (and nothing to undo) on an empty staff
            self.undo_stack.push(RemoveNote(self, part, len(part.notes) - 1))

    # --- Playback -----------------------------------------------------------

    def on_play(self):
        """Slot: play every tab together, or resume if paused."""
        self.player.play(self.score)

    def on_note_started(self, part_index, staff_index, note_index):
        """Slot: move the cursor on that part's tab (on the right staff of a grand staff)."""
        staves = self.staves_in_tab(part_index)  # tab i shows score.parts[i]
        if staff_index < len(staves):
            staves[staff_index].set_playing_index(note_index)

    def on_play_pause(self):
        """Slot for Space: pause if playing, otherwise play."""
        if self.player.state == PLAYING:
            self.player.pause()
        else:
            self.on_play()

    def update_transport_buttons(self, state):
        """Slot: enable only the buttons that make sense in this state.

        A disabled button is grayed out and can't be clicked.
        """
        self.play_action.setEnabled(state != PLAYING)
        self.pause_action.setEnabled(state == PLAYING)
        self.stop_action.setEnabled(state in (PLAYING, PAUSED))
        # "Play" means "Resume" while paused; the label says so.
        self.play_action.setText("Resume" if state == PAUSED else "Play")
        if state == STOPPED:
            for staff in self.all_staffs():
                staff.set_playing_index(None)  # hide every cursor

    def on_time_signature_chosen(self, index):
        """Slot: a time signature was picked in the Time drop-down."""
        time_signature = TIME_SIGNATURES[index]
        if time_signature != self.score.time_signature:  # code setting the box is no new edit
            self.undo_stack.push(
                ChangeTimeSignature(self, self.score.time_signature, time_signature))

    def set_time_signature(self, time_signature):
        """Change the time signature, the Time drop-down, and every staff.

        The notes don't change; every staff simply re-bars them.
        """
        self.score.time_signature = time_signature  # first, so the drop-down sees no new edit
        self.time_box.setCurrentIndex(TIME_SIGNATURES.index(time_signature))
        for staff in self.all_staffs():
            self.update_staff_display(staff)

    def on_key_chosen(self, index):
        """Slot: a key was picked in the Key drop-down."""
        key = self.key_box.itemData(index)
        if key != self.score.key:  # the code setting the box (undo, open) is no new edit
            self.undo_stack.push(ChangeKey(self, self.score.key, key))

    def on_tempo_changed(self, bpm):
        """Slot: the tempo slider moved."""
        # When the code moves the slider (loading a file, undo), the score
        # already has this tempo, so it's not a new edit.
        if bpm != self.score.tempo_bpm:
            self.undo_stack.push(ChangeTempo(self, self.score.tempo_bpm, bpm))
        self.tempo_label.setText(f" {bpm} BPM ")

    # --- Files --------------------------------------------------------------

    def build_file_menu(self):
        """The File menu, in the menu bar along the top of the window."""
        menu = self.menuBar().addMenu("&File")  # & underlines F: Alt+F opens the menu
        # QKeySequence's standard keys are the usual shortcuts for this computer:
        # on Windows, New is Ctrl+N, Open is Ctrl+O, Save is Ctrl+S, and so on.
        for text, shortcut, slot in [
            ("&New", QKeySequence.New, self.new_file),
            ("&Open...", QKeySequence.Open, self.open_file),
            ("&Save", QKeySequence.Save, self.save),
            ("Save &As...", QKeySequence.SaveAs, self.save_as),
            ("&Export MIDI...", QKeySequence("Ctrl+E"), self.export_midi_file),
        ]:
            action = menu.addAction(text)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
        menu.addSeparator()
        menu.addAction("E&xit").triggered.connect(self.close)  # close() runs closeEvent

    def build_edit_menu(self):
        """The Edit menu: Undo and Redo."""
        menu = self.menuBar().addMenu("&Edit")
        # The undo stack makes these actions for us. Their text follows the
        # stack ("Undo Add note", "Redo Move note"), and they gray out
        # by themselves when there's nothing to undo or redo.
        self.undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        self.undo_action.setShortcut(QKeySequence.Undo)  # Ctrl+Z
        self.redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        self.redo_action.setShortcut(QKeySequence.Redo)  # Ctrl+Y
        menu.addAction(self.undo_action)
        menu.addAction(self.redo_action)

        # Raise / lower the note under the mouse. Shortcuts on menu actions
        # work anywhere in the window. On most keyboards "+" is typed as
        # Shift+=, which Qt reports as "Shift" plus "+", so that combination
        # is listed too; plain "=" (the same key without Shift) works as well.
        menu.addSeparator()
        raise_action = menu.addAction("Raise hovered note a half step")
        raise_action.setShortcuts([QKeySequence("+"), QKeySequence("Shift++"), QKeySequence("=")])
        raise_action.triggered.connect(lambda: self.change_hovered_alter(+1))
        lower_action = menu.addAction("Lower hovered note a half step")
        lower_action.setShortcut(QKeySequence("-"))
        lower_action.triggered.connect(lambda: self.change_hovered_alter(-1))

    def change_hovered_alter(self, direction):
        """Raise (+1) or lower (-1) the note under the mouse by a half step."""
        # The staff the mouse is over (a grand staff has two to choose from).
        hovered = [s for s in self.staves_in_tab(self.tabs.currentIndex())
                   if s.hovered_note_index() is not None]
        if self.current_staff().part.instrument.is_drums:
            self.statusBar().showMessage("Drums have no sharps or flats.", 3000)
            return
        if not hovered:
            self.statusBar().showMessage("Point at a note, then press + or -.", 3000)
            return
        staff = hovered[0]
        index = staff.hovered_note_index()
        # Work with the note as it's *shown* (concert pitch view may differ),
        # then convert the result back to written pitch for storing.
        shown = staff.shown.notes[index]
        new_alter = shown.alter + direction
        if not FLAT <= new_alter <= SHARP:  # Python allows chained comparisons like this
            self.statusBar().showMessage("Double sharps and flats aren't supported.", 3000)
            return
        note = staff.part.notes[index]
        old = (note.step, note.alter)
        new = staff.to_written(shown.step, new_alter)
        text = "Raise note" if direction > 0 else "Lower note"
        self.undo_stack.push(SetNotePitch(self, staff.part, index, old, new, text))
        staff.preview_note(note)  # hear the new pitch

    def update_staff_display(self, staff):
        """Show a staff at written pitch, or at concert pitch if that's switched on."""
        part = staff.part
        offset = part.instrument.concert_offset if self.concert_pitch else 0
        # A part shown at concert pitch uses the piece's real key; otherwise its own.
        key = self.score.key if offset else part.written_key(self.score.key)
        staff.set_display(offset, key, self.score.time_signature)

    def on_concert_pitch_toggled(self, checked):
        """Slot: the Concert Pitch switch was flipped (a view setting: not saved, not undoable)."""
        self.concert_pitch = checked
        for staff in self.all_staffs():
            self.update_staff_display(staff)

    def update_title(self):
        """Show the file name, plus * if there are unsaved changes."""
        name = display_name(self.file_path) if self.file_path else "Untitled"
        # Qt shows "[*]" as "*" when the window is marked modified, and hides it otherwise.
        self.setWindowTitle(f"{name}[*] - Music Staff")
        # "Clean" means the undo stack is exactly where it was at the last save.
        self.setWindowModified(not self.undo_stack.isClean())

    def show_score(self, score, path):
        """Replace everything on screen with this score (after New or Open)."""
        self.player.stop()
        while self.tabs.count():  # remove every old tab
            area = self.tabs.widget(0)
            self.tabs.removeTab(0)
            area.deleteLater()
        self.score = score
        self.file_path = path
        if not score.parts:
            score.add_part(GRAND_PIANO)  # a score always has at least one instrument
        for part in score.parts:
            self.show_part(part)
        self.tabs.setCurrentIndex(0)
        self.tempo_slider.setValue(score.tempo_bpm)
        self.on_tempo_changed(score.tempo_bpm)  # updates the label even if the value didn't change
        self.set_key(score.key)
        self.set_time_signature(score.time_signature)
        # A different score: the old undo history no longer applies. clear()
        # also marks the stack clean, so there's nothing unsaved.
        self.undo_stack.clear()
        self.update_title()

    def maybe_save(self):
        """Before throwing the current score away: offer to save it.

        Returns True if it's OK to go ahead (saved or discarded), False to cancel.
        """
        if not self.isWindowModified():
            return True  # nothing unsaved
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save your changes before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,  # | combines the buttons
        )
        if answer == QMessageBox.Save:
            return self.save()  # False if the user cancels the Save dialog
        return answer == QMessageBox.Discard

    def new_file(self):
        if self.maybe_save():
            self.show_score(Score(), None)

    def open_file(self):
        if not self.maybe_save():
            return
        # getOpenFileName shows the standard Windows Open dialog. It returns the
        # chosen path (or "" if cancelled) and which filter was used; "_" is
        # Python's name for a value we don't need.
        path, _ = QFileDialog.getOpenFileName(self, "Open", self.start_folder(), FILE_FILTER)
        if not path:
            return
        try:
            score = load_score(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Couldn't open file", f"{path}\n\n{error}")
            return
        self.show_score(score, path)

    def save(self):
        """Save to the current file, or ask where if it's never been saved.

        Returns True if the score was saved.
        """
        if self.file_path is None:
            return self.save_as()
        return self.write_file(self.file_path)

    def save_as(self):
        """Ask for a file name, then save there. Returns True if saved."""
        path, _ = QFileDialog.getSaveFileName(self, "Save As", self.start_folder(), FILE_FILTER)
        if not path:
            return False  # cancelled
        if not path.endswith(FILE_EXTENSION):
            path = str(Path(path).with_suffix("")) + FILE_EXTENSION
        return self.write_file(path)

    def export_midi_file(self):
        """Save the score as a standard .mid file other music programs can open."""
        # Suggest the score's own name, e.g. "Hot Cross Buns.mid".
        name = display_name(self.file_path) if self.file_path else "Untitled"
        suggested = str(Path(self.start_folder()) / f"{name}.mid")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export MIDI", suggested, "MIDI files (*.mid);;All files (*)")
        if not path:
            return  # cancelled
        if not path.lower().endswith(".mid"):
            path += ".mid"
        try:
            export_midi(self.score, path)
        except OSError as error:
            QMessageBox.warning(self, "Couldn't export MIDI", f"{path}\n\n{error}")
            return
        self.statusBar().showMessage(f"Exported {path}", 3000)

    def write_file(self, path):
        try:
            save_score(self.score, path)
        except OSError as error:  # e.g. the folder is read-only or the disk is full
            QMessageBox.warning(self, "Couldn't save file", f"{path}\n\n{error}")
            return False
        self.file_path = path
        self.undo_stack.setClean()  # "this is the saved state"; undoing past it brings the * back
        self.update_title()         # the file name may have changed (Save As)
        self.statusBar().showMessage(f"Saved {path}", 3000)
        return True

    def start_folder(self):
        """Where file dialogs open: next to the current file, else in saved_music."""
        if self.file_path:
            return str(Path(self.file_path).parent)
        # Create the folder if it's missing (e.g. a fresh copy from GitHub).
        # exist_ok=True: no error if it's already there.
        SAVED_MUSIC_FOLDER.mkdir(exist_ok=True)
        return str(SAVED_MUSIC_FOLDER)

    def closeEvent(self, event):
        # Qt calls this when the window is about to close: a chance to clean up.
        if not self.maybe_save():
            event.ignore()  # the user chose Cancel: keep the window open
            return
        self.player.close()
        super().closeEvent(event)  # then let QMainWindow finish closing


def main():
    app = QApplication(sys.argv)  # every Qt program needs exactly one of these

    window = MainWindow()
    window.resize(800, 540)  # tall enough for 3 toolbar rows and a grand staff's two staves
    window.show()

    # Start the event loop: Qt now waits for clicks, key presses, and repaint
    # requests, and calls our code when they happen. This line only returns
    # when the window is closed.
    sys.exit(app.exec())


# This is true only when the file is run directly (python main.py),
# not when another file imports it.
if __name__ == "__main__":
    main()
