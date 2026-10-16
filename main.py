"""Music staff app: the program's starting point. Run with: python main.py"""

import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QActionGroup, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from model import EIGHTH, HALF, QUARTER, WHOLE, Note, Part  # our own model.py
from player import Player

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
FIRST_NOTE_X = MARGIN + 60  # leaves room at the start for a clef later
NOTE_SPACING = 40           # distance from one note to the next

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

    def __init__(self):
        # __init__ runs once, when the widget is created.
        super().__init__()  # first, let QWidget set itself up
        # The music being shown. The widget only draws it and edits it;
        # what a note *is* lives in model.py.
        self.part = Part()
        # The duration that the next click will use. The toolbar changes it.
        self.current_duration = QUARTER
        # When True, clicks add rests instead of notes. The Rest button changes it.
        self.rest_mode = False

    def note_x(self, index):
        """The x position of the note at this place in the list (0 = first)."""
        return FIRST_NOTE_X + index * NOTE_SPACING

    def note_index_at(self, x):
        """The reverse of note_x: which note is at this x position?

        Returns the note's index, or None if there's no note there.
        """
        index = round((x - FIRST_NOTE_X) / NOTE_SPACING)
        if 0 <= index < len(self.part.notes):
            return index
        return None

    def delete_last_note(self):
        """Remove the last note and redraw."""
        self.part.remove_last()
        self.update()

    def mousePressEvent(self, event):
        # Qt calls this automatically whenever the mouse is clicked on us.
        if event.button() == Qt.RightButton:
            # Right-click deletes the note in that column, if there is one.
            index = self.note_index_at(event.position().x())
            if index is not None:  # "is not None", because index 0 is a real note
                self.part.remove_note(index)
                self.update()
            return
        if event.button() != Qt.LeftButton:
            return
        # Ignore the click if the next note wouldn't fit before the right edge.
        # (Scrolling for longer pieces comes in a later milestone.)
        if self.note_x(len(self.part.notes)) > self.width() - MARGIN:
            return
        if self.rest_mode:
            step = None  # a rest has no pitch, so the click's height doesn't matter
        else:
            step = y_to_step(event.position().y())
        self.part.add_note(Note(step, self.current_duration))
        self.update()  # ask Qt to repaint soon; it will call paintEvent

    def paintEvent(self, event):
        # Qt calls paintEvent automatically whenever the widget needs to be
        # drawn: when the window first opens, is resized, or uncovered.
        # We never call it ourselves.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # smooth edges
        painter.fillRect(self.rect(), Qt.white)        # paper background
        painter.setPen(QPen(Qt.black, 1))

        right_edge = self.width() - MARGIN
        for step in range(0, TOP_LINE_STEP + 1, 2):  # steps 0, 2, 4, 6, 8
            y = step_to_y(step)
            painter.drawLine(QPointF(MARGIN, y), QPointF(right_edge, y))

        # Draw every note. The whole picture is redrawn from self.part each
        # time, so the model is the "truth" and the picture just shows it.
        # enumerate gives each item along with its position: (0, first), (1, second), ...
        for index, note in enumerate(self.part.notes):
            self.draw_note(painter, self.note_x(index), note)

        # Bar lines: the model says where measures end; we draw a line
        # halfway between that note and the next one.
        painter.setPen(QPen(Qt.black, 1))
        for index in self.part.measure_ends():
            x = self.note_x(index) + NOTE_SPACING / 2
            painter.drawLine(QPointF(x, step_to_y(TOP_LINE_STEP)), QPointF(x, step_to_y(0)))

    def draw_note(self, painter, x, note):
        """Draw one note at horizontal position x, shaped by its duration."""
        if note.is_rest:
            self.draw_rest(painter, x, note.duration)
            return

        y = step_to_y(note.step)
        self.draw_ledger_lines(painter, x, note.step)

        # Note head: whole and half notes are hollow; shorter notes are filled.
        # The pen draws outlines; the brush fills the inside.
        if note.duration >= HALF:
            painter.setPen(QPen(Qt.black, 1.8))  # thicker outline for hollow heads
            painter.setBrush(Qt.NoBrush)
        else:
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(Qt.black)
        painter.drawEllipse(QPointF(x, y), NOTE_HEAD_WIDTH / 2, NOTE_HEAD_HEIGHT / 2)
        painter.setPen(QPen(Qt.black, 1))

        if note.duration == WHOLE:
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

        if note.duration == EIGHTH:
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
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setPen(QPen(Qt.black, 1))

    def draw_rest(self, painter, x, duration):
        """Draw the rest symbol for this duration, centered at horizontal position x.

        Rests sit at fixed heights on the staff. Positions are given in staff
        steps (halves like 5.5 are allowed) so they scale with LINE_SPACING.
        """
        s = LINE_SPACING
        if duration == WHOLE:
            # A block hanging down from the 4th line (step 6).
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawRect(QRectF(x - s * 0.5, step_to_y(6), s, s * 0.5))
        elif duration == HALF:
            # A block sitting on top of the middle line (step 4).
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawRect(QRectF(x - s * 0.5, step_to_y(4) - s * 0.5, s, s * 0.5))
        elif duration == QUARTER:
            # A thick zig-zag with a small hook at the bottom.
            path = QPainterPath(QPointF(x - s * 0.15, step_to_y(7)))
            path.lineTo(x + s * 0.3, step_to_y(5.5))
            path.lineTo(x - s * 0.25, step_to_y(4))
            path.lineTo(x + s * 0.25, step_to_y(2.5))
            path.quadTo(QPointF(x - s * 0.55, step_to_y(2.4)), QPointF(x + s * 0.05, step_to_y(1)))
            painter.setPen(QPen(Qt.black, s * 0.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        elif duration == EIGHTH:
            # A dot, a small curl to the right, then a slanted stroke down-left.
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawEllipse(QPointF(x - s * 0.25, step_to_y(5)), s * 0.18, s * 0.18)
            path = QPainterPath(QPointF(x - s * 0.25, step_to_y(4.7)))
            path.quadTo(QPointF(x + s * 0.1, step_to_y(4.5)), QPointF(x + s * 0.35, step_to_y(5.3)))
            path.lineTo(x - s * 0.05, step_to_y(2))
            painter.setPen(QPen(Qt.black, 1.6))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        painter.setPen(QPen(Qt.black, 1))  # put the normal pen back for whatever is drawn next

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


class MainWindow(QMainWindow):
    """The application window: a toolbar on top, the staff in the middle.

    QMainWindow already has places for toolbars, menus, and a status bar;
    we fill them in.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Staff")

        self.staff = StaffWidget()
        self.setCentralWidget(self.staff)  # the staff fills the middle

        toolbar = self.addToolBar("Durations")
        # A QActionGroup makes its buttons work like radio buttons:
        # checking one automatically unchecks the others.
        self.duration_group = QActionGroup(self)
        for label, duration, shortcut in DURATION_CHOICES:
            action = QAction(f"{label} ({shortcut})", self)
            action.setCheckable(True)        # stays pressed in when chosen
            action.setShortcut(shortcut)     # pressing the key = clicking the button
            action.setData(duration)         # remember which duration this button means
            action.setChecked(duration == self.staff.current_duration)
            self.duration_group.addAction(action)
            toolbar.addAction(action)

        # Signals and slots: when any button in the group is triggered (clicked
        # or chosen by its shortcut), Qt calls our method with that button.
        # "connect" is how we say "when this happens, call that."
        self.duration_group.triggered.connect(self.on_duration_chosen)

        # The Rest button is a separate on/off switch, not part of the group,
        # so it combines with whichever duration is chosen.
        toolbar.addSeparator()  # a small divider line in the toolbar
        self.rest_action = QAction("Rest (R)", self)
        self.rest_action.setCheckable(True)
        self.rest_action.setShortcut("R")
        # toggled is a different signal: it sends True when switched on, False when off.
        self.rest_action.toggled.connect(self.on_rest_toggled)
        toolbar.addAction(self.rest_action)

        toolbar.addSeparator()
        self.delete_last_action = QAction("Delete Last (Backspace)", self)
        self.delete_last_action.setShortcut("Backspace")
        # A slot can be any method, even one on another object.
        self.delete_last_action.triggered.connect(self.staff.delete_last_note)
        toolbar.addAction(self.delete_last_action)

        self.player = Player()
        toolbar.addSeparator()
        self.play_action = QAction("Play (Space)", self)
        self.play_action.setShortcut("Space")
        self.play_action.triggered.connect(self.on_play)
        toolbar.addAction(self.play_action)

    def on_duration_chosen(self, action):
        """Slot: called by Qt when a duration button is chosen."""
        self.staff.current_duration = action.data()

    def on_rest_toggled(self, checked):
        """Slot: called by Qt when the Rest button is switched on or off."""
        self.staff.rest_mode = checked

    def on_play(self):
        """Slot: play the staff from the beginning."""
        self.player.play(self.staff.part)

    def closeEvent(self, event):
        # Qt calls this when the window is about to close: a chance to clean up.
        self.player.close()
        super().closeEvent(event)  # then let QMainWindow finish closing


def main():
    app = QApplication(sys.argv)  # every Qt program needs exactly one of these

    window = MainWindow()
    window.resize(800, 240)
    window.show()

    # Start the event loop: Qt now waits for clicks, key presses, and repaint
    # requests, and calls our code when they happen. This line only returns
    # when the window is closed.
    sys.exit(app.exec())


# This is true only when the file is run directly (python main.py),
# not when another file imports it.
if __name__ == "__main__":
    main()
