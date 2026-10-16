"""Music staff app: the program's starting point. Run with: python main.py"""

import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

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
        # The notes placed so far, as a list of staff steps, e.g. [0, 4, -2].
        # Only the pitch is stored; where to draw each note is worked out
        # from its step and its place in the list.
        self.notes = []

    def note_x(self, index):
        """The x position of the note at this place in the list (0 = first)."""
        return FIRST_NOTE_X + index * NOTE_SPACING

    def mousePressEvent(self, event):
        # Qt calls this automatically whenever the mouse is clicked on us.
        if event.button() != Qt.LeftButton:
            return
        # Ignore the click if the next note wouldn't fit before the right edge.
        # (Scrolling for longer pieces comes in a later milestone.)
        if self.note_x(len(self.notes)) > self.width() - MARGIN:
            return
        self.notes.append(y_to_step(event.position().y()))
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

        # Draw every note. The whole picture is redrawn from self.notes each
        # time, so the list is the "truth" and the picture just shows it.
        painter.setBrush(Qt.black)  # brush = fill color for shapes
        # enumerate gives each item along with its position: (0, first), (1, second), ...
        for index, step in enumerate(self.notes):
            self.draw_quarter_note(painter, self.note_x(index), step)

    def draw_quarter_note(self, painter, x, step):
        """Draw a quarter note at horizontal position x on the given staff step."""
        y = step_to_y(step)
        self.draw_ledger_lines(painter, x, step)
        painter.drawEllipse(QPointF(x, y), NOTE_HEAD_WIDTH / 2, NOTE_HEAD_HEIGHT / 2)

        # Notation rule: notes below the middle line have stems going up on
        # the right; notes on or above it have stems going down on the left.
        if step < MIDDLE_LINE_STEP:
            stem_x = x + NOTE_HEAD_WIDTH / 2 - 0.5
            stem_end_y = y - STEM_LENGTH
        else:
            stem_x = x - NOTE_HEAD_WIDTH / 2 + 0.5
            stem_end_y = y + STEM_LENGTH
        painter.drawLine(QPointF(stem_x, y), QPointF(stem_x, stem_end_y))

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


def main():
    app = QApplication(sys.argv)  # every Qt program needs exactly one of these

    window = StaffWidget()
    window.setWindowTitle("Music Staff")
    window.resize(800, 200)
    window.show()

    # Start the event loop: Qt now waits for clicks, key presses, and repaint
    # requests, and calls our code when they happen. This line only returns
    # when the window is closed.
    sys.exit(app.exec())


# This is true only when the file is run directly (python main.py),
# not when another file imports it.
if __name__ == "__main__":
    main()
