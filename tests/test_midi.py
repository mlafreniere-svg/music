"""Tests for midi_export.py.

To check the bytes, this file has a small MIDI *reader* (read_midi) that
decodes a file back into events, following the same public standard.
"""

import struct

from midi_export import TICKS_PER_BEAT, export_midi, score_to_midi, variable_length
from model import HALF, QUARTER, SHARP, Note, Score, find_instrument


def read_variable_length(data, pos):
    """Decode a variable-length number starting at data[pos]; return (number, new pos)."""
    number = 0
    while True:
        byte = data[pos]
        pos += 1
        number = (number << 7) | (byte & 0x7F)
        if not byte & 0x80:  # top bit clear: this was the last byte
            return number, pos


def read_midi(data):
    """Decode MIDI bytes into (header, tracks); each track is a list of
    (absolute tick, event bytes)."""
    assert data[:4] == b"MThd"
    length, fmt, ntracks, division = struct.unpack(">IHHH", data[4:14])
    pos = 8 + length
    tracks = []
    for _ in range(ntracks):
        assert data[pos:pos + 4] == b"MTrk"
        (size,) = struct.unpack(">I", data[pos + 4:pos + 8])
        pos += 8
        end = pos + size
        tick, events = 0, []
        while pos < end:
            delta, pos = read_variable_length(data, pos)
            tick += delta
            status = data[pos]
            if status == 0xFF:                      # meta event: FF type length data
                meta_len, data_start = read_variable_length(data, pos + 2)
                event_end = data_start + meta_len
            elif status & 0xF0 == 0xC0:             # program change: 2 bytes
                event_end = pos + 2
            else:                                   # note on / note off: 3 bytes
                event_end = pos + 3
            events.append((tick, data[pos:event_end]))
            pos = event_end
        tracks.append(events)
    return (fmt, ntracks, division), tracks


def notes_in(track):
    """(start tick, end tick, channel, pitch) for each note in a track."""
    started, notes = {}, []
    for tick, event in track:
        kind, channel = event[0] & 0xF0, event[0] & 0x0F
        if kind == 0x90:
            started[(channel, event[1])] = tick
        elif kind == 0x80:
            notes.append((started.pop((channel, event[1])), tick, channel, event[1]))
    return sorted(notes)


def test_variable_length_numbers():
    assert variable_length(0) == b"\x00"
    assert variable_length(127) == b"\x7f"
    assert variable_length(128) == b"\x81\x00"
    assert variable_length(200) == b"\x81\x48"
    assert variable_length(16383) == b"\xff\x7f"


def test_header_and_track_count():
    score = Score()
    score.add_part(find_instrument("Violin"))
    score.add_part(find_instrument("Cello"))
    (fmt, ntracks, division), tracks = read_midi(score_to_midi(score))
    assert (fmt, ntracks, division) == (1, 3, TICKS_PER_BEAT)  # conductor + 2 parts
    assert all(track[-1][1] == b"\xff\x2f\x00" for track in tracks)  # each ends properly


def test_tempo_time_and_key_signature():
    score = Score(tempo_bpm=120, key=-2)
    score.add_part(find_instrument("Violin"))
    _, tracks = read_midi(score_to_midi(score))
    conductor = dict((event[1], event[3:]) for _, event in tracks[0] if event[0] == 0xFF)
    assert int.from_bytes(conductor[0x51], "big") == 500_000   # 0.5 s per beat
    assert conductor[0x58][:2] == bytes([4, 2])                # 4/4
    assert struct.unpack(">bB", conductor[0x59]) == (-2, 0)     # 2 flats, major


def test_notes_have_the_right_times_and_pitches():
    score = Score()
    violin = score.add_part(find_instrument("Violin"))
    violin.notes = [Note(-2), Note(None), Note(1, HALF, SHARP)]  # C4, rest, F#4 half
    _, tracks = read_midi(score_to_midi(score))
    assert notes_in(tracks[1]) == [
        (0, 480, 0, 60),     # C4 for one beat
        (960, 1920, 0, 66),  # after a beat of rest: F#4 for two beats
    ]


def test_part_name_and_instrument():
    score = Score()
    score.add_part(find_instrument("Electric Guitar"))
    _, tracks = read_midi(score_to_midi(score))
    events = [event for _, event in tracks[1]]
    assert b"\xff\x03" + bytes([len("Electric Guitar")]) + b"Electric Guitar" in events
    assert bytes([0xC0, 27]) in events  # program change to clean electric guitar


def test_transposing_instruments_export_sounding_pitch():
    score = Score()
    score.add_part(find_instrument("Trumpet in B♭")).notes = [Note(-1)]  # written D4
    _, tracks = read_midi(score_to_midi(score))
    assert notes_in(tracks[1])[0][3] == 60  # sounds C4


def test_drums_go_on_channel_10():
    score = Score()
    score.add_part(find_instrument("Violin")).notes = [Note(0)]
    score.add_part(find_instrument("Drum Kit")).notes = [Note(1), Note(5)]  # kick, snare
    score.add_part(find_instrument("Cello")).notes = [Note(0)]
    _, tracks = read_midi(score_to_midi(score))
    assert [n[2] for n in notes_in(tracks[2])] == [9, 9]   # MIDI channel 10 (counted from 1)
    assert [n[3] for n in notes_in(tracks[2])] == [36, 38]  # kick, snare
    assert notes_in(tracks[3])[0][2] == 1                   # cello still gets its own channel


def test_tied_note_is_one_long_note():
    score = Score()
    score.add_part(find_instrument("Violin")).notes = [Note(0)] * 3 + [Note(0, HALF)]
    _, tracks = read_midi(score_to_midi(score))
    assert notes_in(tracks[1])[-1][:2] == (1440, 2400)  # one 2-beat note across the bar line


def test_repeated_note_is_released_before_replaying():
    score = Score()
    score.add_part(find_instrument("Violin")).notes = [Note(0, QUARTER), Note(0, QUARTER)]
    _, tracks = read_midi(score_to_midi(score))
    at_480 = [event[0] & 0xF0 for tick, event in tracks[1] if tick == 480]
    assert at_480 == [0x80, 0x90]  # off, then on


def test_export_writes_a_file(tmp_path):
    score = Score()
    score.add_part(find_instrument("Violin")).notes = [Note(0)]
    path = tmp_path / "song.mid"
    export_midi(score, path)
    assert path.read_bytes() == score_to_midi(score)
