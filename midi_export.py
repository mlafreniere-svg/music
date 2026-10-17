"""Export a score as a standard MIDI file (.mid), written byte by byte.

A MIDI file is a *binary* file: not text, but a sequence of bytes (numbers
from 0 to 255). Its layout is a public standard, so any music program can
read it. It's made of "chunks", each starting with a 4-letter name:

    MThd  the header: format, number of tracks, ticks per beat
    MTrk  a track: a list of events, each with the time since the previous one

We write a "format 1" file: track 0 holds the tempo, time signature and key
signature; then one track per part holds its name, instrument, and notes.
"""

import struct

from model import BEATS_PER_MEASURE

TICKS_PER_BEAT = 480  # how finely time is counted: 480 ticks per quarter note
VELOCITY = 100        # how hard each note is played, 0-127
MIDI_DRUM_CHANNEL = 9  # "channel 10" to musicians; every program plays drums there
# Every other channel, for melodic parts.
MELODIC_CHANNELS = [c for c in range(16) if c != MIDI_DRUM_CHANNEL]


def variable_length(number):
    """Encode a number the MIDI way: 7 bits per byte, as few bytes as possible.

    Each byte holds 7 bits of the number; the top bit (128) says "more bytes
    follow". So 0-127 take one byte, 128-16383 take two, and so on.
    Example: 200 = 1*128 + 72 -> bytes 0x81 0x48.
    """
    groups = [number & 0x7F]  # & 0x7F keeps the lowest 7 bits
    number >>= 7               # >> shifts the bits right: drops the 7 we just took
    while number:
        groups.append((number & 0x7F) | 0x80)  # | 0x80 sets the "more follows" bit
        number >>= 7
    return bytes(reversed(groups))  # the most significant group comes first


def meta_event(kind, data):
    """A "meta" event: information about the music, not a sound (tempo, names...)."""
    return bytes([0xFF, kind]) + variable_length(len(data)) + data


def track_chunk(events):
    """Build an MTrk chunk from (tick, order, event bytes) tuples.

    Events are sorted by tick; `order` breaks ties (note-offs before note-ons,
    so a repeated note is released before it's played again). Each event is
    stored with the number of ticks since the previous one (its "delta time").
    """
    data = b""  # b"..." is a bytes value, the binary cousin of a string
    previous_tick = 0
    for tick, _, event in sorted(events, key=lambda e: (e[0], e[1])):
        data += variable_length(tick - previous_tick) + event
        previous_tick = tick
    data += variable_length(0) + meta_event(0x2F, b"")  # "end of track"
    # struct.pack(">I", n) writes n as 4 bytes, biggest byte first (">").
    return b"MTrk" + struct.pack(">I", len(data)) + data


def conductor_track(score):
    """Track 0: tempo, time signature, and key signature, all at the start."""
    microseconds_per_beat = round(60_000_000 / score.tempo_bpm)  # _ makes big numbers readable
    tempo = meta_event(0x51, microseconds_per_beat.to_bytes(3, "big"))
    # Time signature: 4/4. Written as numerator, log2(denominator), then two
    # standard values (24 MIDI clocks per click, 8 32nd notes per quarter).
    time_signature = meta_event(0x58, bytes([BEATS_PER_MEASURE, 2, 24, 8]))
    # Key signature: number of sharps (negative = flats) as a signed byte, then 0 = major.
    key_signature = meta_event(0x59, struct.pack(">bB", score.key, 0))
    return track_chunk([(0, 0, tempo), (0, 0, time_signature), (0, 0, key_signature)])


def part_track(part, channel):
    """One part: its name, its instrument, and every note (at sounding pitch)."""
    events = [
        (0, 0, meta_event(0x03, part.instrument.name.encode("utf-8"))),  # track name
        (0, 0, bytes([0xC0 | channel, part.instrument.program])),       # program change
    ]
    for staff in part.staves():  # a grand staff's two hands share the track
        beat = 0.0
        for note in staff.notes:
            pitch = staff.sounding_pitch(note)  # transposing instruments: what you hear
            start = round(beat * TICKS_PER_BEAT)
            end = round((beat + note.duration) * TICKS_PER_BEAT)
            if pitch is not None and 0 <= pitch <= 127:  # rests make no events
                # A status byte is the event type (0x90 note-on, 0x80 note-off)
                # combined with the channel number (0-15) in its low 4 bits.
                events.append((start, 1, bytes([0x90 | channel, pitch, VELOCITY])))
                events.append((end, 0, bytes([0x80 | channel, pitch, 0])))
            beat += note.duration
    return track_chunk(events)


def score_to_midi(score):
    """The whole score as the bytes of a MIDI file."""
    tracks = [conductor_track(score)]
    melodic = iter(MELODIC_CHANNELS)  # hands out channels one at a time with next()
    for part in score.parts:
        channel = MIDI_DRUM_CHANNEL if part.instrument.is_drums else next(melodic)
        tracks.append(part_track(part, channel))
    # Header: chunk length 6, format 1, number of tracks, ticks per beat.
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), TICKS_PER_BEAT)
    return header + b"".join(tracks)


def export_midi(score, path):
    """Write the score to a .mid file. "wb" = write, binary (bytes, not text)."""
    with open(path, "wb") as file:
        file.write(score_to_midi(score))
