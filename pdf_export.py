"""Print the score to a PDF file: each instrument in turn, on US Letter pages.

On screen, each staff is one long line you scroll along. On paper it has to
be broken into lines ("systems") that fit the page. Instead of drawing the
music a second time, we reuse the screen drawing: each staff is drawn into
the PDF in slices, cut at bar lines. Every line starts with a copy of the
staff's beginning (brace, clef, key and time signature), then as many whole
measures as fit.

This file only arranges slices on pages; it doesn't know about notes. The
window gives it Sections: a heading plus a finished widget to slice.
"""

from dataclasses import dataclass

from PySide6.QtCore import QMarginsF, QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPdfWriter

SCREEN_DPI = 96   # our drawing is in screen pixels: 96 per inch
MARGIN_INCHES = 0.6
LINE_GAP = 6      # space between printed lines (pixels)
HEADING_GAP = 10  # space under an instrument's name


@dataclass
class Section:
    """One instrument's music, ready to slice.

    `widget` is drawn (a StaffWidget, or a GrandStaffWidget for two staves);
    `staff` is the staff whose bar lines decide where lines break (for a
    grand staff, its upper staff: both staves share bar lines).
    """

    heading: str
    widget: object
    staff: object


def export_pdf(path, title, subtitle, sections):
    """Write the sections to a PDF file at `path`."""
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.Letter))
    writer.setPageMargins(QMarginsF(MARGIN_INCHES, MARGIN_INCHES, MARGIN_INCHES, MARGIN_INCHES),
                          QPageLayout.Inch)
    writer.setTitle(title)

    painter = QPainter(writer)
    # The PDF counts in its own tiny units (writer.resolution() per inch). Scaling
    # by resolution / 96 lets us keep drawing in screen pixels.
    scale = writer.resolution() / SCREEN_DPI
    painter.scale(scale, scale)
    page = writer.pageLayout().paintRectPixels(writer.resolution())  # the area inside the margins
    page_width = page.width() / scale
    page_height = page.height() / scale

    y = draw_title(painter, title, subtitle, page_width)
    for section in sections:
        lines = break_into_lines(section, page_width)
        line_height = section.widget.height()
        # Keep the heading with the first line of music.
        if y + heading_height() + line_height > page_height:
            writer.newPage()
            y = 0
        y = draw_heading(painter, section.heading, y)
        for pieces in lines:
            if y + line_height > page_height:  # no room: continue on a new page
                writer.newPage()
                y = 0
            x = 0
            for left, right in pieces:  # each piece is a slice of the widget: [left, right)
                draw_slice(painter, section.widget, left, right, x, y, line_height)
                x += right - left
            y += line_height + LINE_GAP
        y += HEADING_GAP
    painter.end()


def draw_slice(painter, widget, left, right, x, y, height):
    """Draw the strip of `widget` between x=left and x=right at (x, y) on the page.

    QWidget.render() has a "source region" argument for this, but when the
    output is a PDF it's ignored and the whole widget is drawn. So we do it
    ourselves: clip the painter to the strip's place on the page, shift
    ("translate") the drawing so the widget's x=left lands there, and draw.
    """
    painter.save()  # remember the painter's settings, to restore them after
    painter.setClipRect(QRectF(x, y, right - left, height))
    painter.translate(x - left, y)
    widget.render(painter, QPoint(0, 0))
    painter.restore()


def break_into_lines(section, page_width):
    """Plan the printed lines for one section.

    Returns a list of lines; each line is a list of (left, right) slices of
    the widget to draw side by side. The first line is the staff's own start
    (brace, clef, key, time signature) plus the first measures; later lines
    repeat the brace, clef and key, then the next measures.
    """
    staff = section.staff
    first_prefix = staff.prefix_right()         # brace, clef, key, time
    later_prefix = staff.line_prefix_right()    # brace, clef, key
    end = staff.music_end_x()
    # Where each measure starts on screen: the first right after the staff's
    # start, the others just after each bar line.
    starts = [first_prefix] + [x + 1 for x in staff.bar_line_xs() if x + 1 < end]
    ends = [x + 1 for x in staff.bar_line_xs()] + [end]  # where each measure ends

    lines = []
    measure = 0
    while measure < len(starts):
        prefix = first_prefix if not lines else later_prefix
        room = page_width - prefix              # width left for measures on this line
        first = measure
        width = ends[measure] - starts[first]
        measure += 1
        # Add measures while the next one still fits (a line always gets at least one).
        while measure < len(starts) and ends[measure] - starts[first] <= room:
            measure += 1
        slices = [(0, prefix), (starts[first], ends[measure - 1])]
        if width > room:
            # A single measure wider than the page: print it anyway, cut at the margin.
            slices[1] = (starts[first], starts[first] + room)
        lines.append(slices)
    return lines


def heading_height():
    return 22 + HEADING_GAP


def draw_title(painter, title, subtitle, page_width):
    """The title (and a line under it) at the top of the first page; returns
    the y where the music can start."""
    font = QFont("Times New Roman")
    font.setPixelSize(30)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, round(page_width), 40), Qt.AlignHCenter | Qt.AlignVCenter, title)
    font.setPixelSize(14)
    font.setBold(False)
    painter.setFont(font)
    painter.drawText(QRect(0, 40, round(page_width), 22), Qt.AlignHCenter | Qt.AlignVCenter, subtitle)
    return 80


def draw_heading(painter, text, y):
    """An instrument's name above its music; returns the y below it."""
    font = QFont("Segoe UI")
    font.setPixelSize(16)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRect(0, round(y), 600, 22), Qt.AlignLeft | Qt.AlignVCenter, text)
    return y + heading_height()
