"""Music staff app: the program's starting point. Run with: python main.py"""

import sys
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMenu, QSlider, QTabBar, QTabWidget,
    QToolButton, QWidget,
)

from model import (  # our own model.py
    EIGHTH, HALF, INSTRUMENTS, PIANO, QUARTER, WHOLE, Note, Score,
)
from player import MAX_PARTS, PAUSED, PLAYING, STOPPED, Player

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
FIRST_NOTE_X = MARGIN + 75  # leaves room at the start for the clef
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

    def set_dimmed(self, dimmed):
        """Draw the staff in gray (dimmed=True) or black."""
        self.ink = DIMMED_INK if dimmed else INK
        self.update()

    def set_playing_index(self, index):
        """Slot: move the playback cursor to this note (None hides it)."""
        self.playing_index = index
        self.update()

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
        if self.settings.rest_mode:
            step = None  # a rest has no pitch, so the click's height doesn't matter
        else:
            step = y_to_step(event.position().y())
        self.part.add_note(Note(step, self.settings.duration))
        self.update()  # ask Qt to repaint soon; it will call paintEvent

    def paintEvent(self, event):
        # Qt calls paintEvent automatically whenever the widget needs to be
        # drawn: when the window first opens, is resized, or uncovered.
        # We never call it ourselves.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # smooth edges
        painter.fillRect(self.rect(), Qt.white)        # paper background

        # The cursor goes first, so the staff and notes are drawn on top of it.
        if self.playing_index is not None:
            x = self.note_x(self.playing_index)
            top = step_to_y(HIGHEST_STEP + 2)
            bottom = step_to_y(LOWEST_STEP - 2)
            painter.fillRect(QRectF(x - NOTE_SPACING / 2, top, NOTE_SPACING, bottom - top), CURSOR_COLOR)

        painter.setPen(QPen(self.ink, 1))

        right_edge = self.width() - MARGIN
        for step in range(0, TOP_LINE_STEP + 1, 2):  # steps 0, 2, 4, 6, 8
            y = step_to_y(step)
            painter.drawLine(QPointF(MARGIN, y), QPointF(right_edge, y))
        self.draw_clef(painter)

        # Draw every note. The whole picture is redrawn from self.part each
        # time, so the model is the "truth" and the picture just shows it.
        # enumerate gives each item along with its position: (0, first), (1, second), ...
        for index, note in enumerate(self.part.notes):
            self.draw_note(painter, self.note_x(index), note)

        # Bar lines: the model says where measures end; we draw a line
        # halfway between that note and the next one.
        painter.setPen(QPen(self.ink, 1))
        for index in self.part.measure_ends():
            x = self.note_x(index) + NOTE_SPACING / 2
            painter.drawLine(QPointF(x, step_to_y(TOP_LINE_STEP)), QPointF(x, step_to_y(0)))

    def draw_clef(self, painter):
        """Draw the part's clef symbol at the start of the staff."""
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
        painter.setFont(font)
        position = QPointF(MARGIN + 8 - outline.left(), top - outline.top())
        painter.drawText(position, symbol)

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
            painter.setPen(QPen(self.ink, 1.8))  # thicker outline for hollow heads
            painter.setBrush(Qt.NoBrush)
        else:
            painter.setPen(QPen(self.ink, 1))
            painter.setBrush(self.ink)
        painter.drawEllipse(QPointF(x, y), NOTE_HEAD_WIDTH / 2, NOTE_HEAD_HEIGHT / 2)
        painter.setPen(QPen(self.ink, 1))

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


class MainWindow(QMainWindow):
    """The application window: toolbars on top, one tab per instrument below.

    QMainWindow already has places for toolbars, menus, and a status bar;
    we fill them in.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Staff")

        self.score = Score()            # all the music: one Part per tab
        self.settings = EditSettings()  # shared by every tab's staff

        # The tabs. Tab number i always shows score.parts[i]: tabs can't be
        # dragged into a new order, so the two lists stay lined up.
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)  # an x on each tab
        self.tabs.tabCloseRequested.connect(self.on_close_tab)
        self.setCentralWidget(self.tabs)

        # The "+ Instrument" button, in the corner beside the tabs. Clicking it
        # opens a menu with one entry per instrument.
        instrument_menu = QMenu(self)
        for instrument in INSTRUMENTS:
            if instrument.name == "Piano (bass)":
                instrument_menu.addSeparator()  # a divider between treble and bass
            action = instrument_menu.addAction(f"{instrument.name}  ({instrument.clef})")
            action.setData(instrument)  # remember which instrument this entry means
        instrument_menu.triggered.connect(self.on_add_instrument)
        add_button = QToolButton()
        add_button.setText("+ Instrument")
        add_button.setMenu(instrument_menu)
        add_button.setPopupMode(QToolButton.InstantPopup)  # open the menu on click
        self.tabs.setCornerWidget(add_button, Qt.TopRightCorner)

        self.add_tab(PIANO)  # every score starts with a piano

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
        self.delete_last_action.triggered.connect(self.on_delete_last)
        toolbar.addAction(self.delete_last_action)

        # Transport controls: the buttons that control playback. They get
        # their own toolbar, on a second row (one long row didn't fit).
        self.player = Player()
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
        self.tempo_slider.setValue(self.player.tempo_bpm)
        self.tempo_slider.setFixedWidth(150)
        self.tempo_slider.setFocusPolicy(Qt.NoFocus)  # keep Space for play/pause
        toolbar.addWidget(self.tempo_slider)
        self.tempo_label = QLabel()
        toolbar.addWidget(self.tempo_label)
        # valueChanged sends the slider's new number every time it moves.
        self.tempo_slider.valueChanged.connect(self.on_tempo_changed)
        self.on_tempo_changed(self.tempo_slider.value())  # show the starting value

        # Keep the buttons and the cursor in step with the player.
        self.player.state_changed.connect(self.update_transport_buttons)
        self.player.note_started.connect(self.on_note_started)
        self.update_transport_buttons(self.player.state)

    # --- Tabs ---------------------------------------------------------------

    def current_staff(self):
        """The staff in the tab that's open right now."""
        return self.tabs.currentWidget()

    def add_tab(self, instrument):
        """Add a part for this instrument to the score, with a tab to show it."""
        part = self.score.add_part(instrument)
        staff = StaffWidget(part, self.settings)
        index = self.tabs.addTab(staff, self.unused_tab_label(instrument.name))
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
        for index, staff in enumerate(self.all_staffs()):
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
        """Every tab's staff, in tab order."""
        return [self.tabs.widget(i) for i in range(self.tabs.count())]

    def on_add_instrument(self, action):
        """Slot: an instrument was chosen from the "+ Instrument" menu."""
        if len(self.score.parts) >= MAX_PARTS:
            # The status bar is the strip along the bottom of the window.
            self.statusBar().showMessage(f"At most {MAX_PARTS} instruments.", 3000)
            return
        self.add_tab(action.data())

    def on_close_tab(self, index):
        """Slot: the x on a tab was clicked."""
        if self.tabs.count() == 1:
            self.statusBar().showMessage("A score needs at least one instrument.", 3000)
            return
        if self.player.state != STOPPED:
            # Removing a part renumbers the ones after it, which would mix up
            # the player's part numbers. Stopping first keeps things simple.
            self.player.stop()
        staff = self.tabs.widget(index)
        self.tabs.removeTab(index)
        self.score.remove_part(index)  # keep the score lined up with the tabs
        staff.deleteLater()  # free the widget once Qt is done with it
        self.refresh_audibility()  # closing a soloed tab un-silences the others

    # --- Editing ------------------------------------------------------------

    def on_duration_chosen(self, action):
        """Slot: called by Qt when a duration button is chosen."""
        self.settings.duration = action.data()

    def on_rest_toggled(self, checked):
        """Slot: called by Qt when the Rest button is switched on or off."""
        self.settings.rest_mode = checked

    def on_delete_last(self):
        """Slot: delete the last note in the open tab."""
        self.current_staff().delete_last_note()

    # --- Playback -----------------------------------------------------------

    def on_play(self):
        """Slot: play every tab together, or resume if paused."""
        self.player.play(self.score)

    def on_note_started(self, part_index, note_index):
        """Slot: move the cursor on that part's tab."""
        staff = self.tabs.widget(part_index)  # tab i shows score.parts[i]
        if staff is not None:
            staff.set_playing_index(note_index)

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

    def on_tempo_changed(self, bpm):
        """Slot: the tempo slider moved."""
        self.player.tempo_bpm = bpm  # takes effect from the next note
        self.tempo_label.setText(f" {bpm} BPM ")

    def closeEvent(self, event):
        # Qt calls this when the window is about to close: a chance to clean up.
        self.player.close()
        super().closeEvent(event)  # then let QMainWindow finish closing


def main():
    app = QApplication(sys.argv)  # every Qt program needs exactly one of these

    window = MainWindow()
    window.resize(800, 270)
    window.show()

    # Start the event loop: Qt now waits for clicks, key presses, and repaint
    # requests, and calls our code when they happen. This line only returns
    # when the window is closed.
    sys.exit(app.exec())


# This is true only when the file is run directly (python main.py),
# not when another file imports it.
if __name__ == "__main__":
    main()
