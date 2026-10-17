"""Automated tests for model.py. Run them all with: python -m pytest

pytest finds every function whose name starts with test_ and runs it.
Each `assert` must be true; if one isn't, pytest reports that test as
failed and shows the values involved.
"""

import pytest

from model import (
    EIGHTH, FLAT, HALF, INSTRUMENTS, KEY_NAMES, NATURAL, PIANO, QUARTER, SHARP, WHOLE,
    Note, Part, Score, clef_change_shift, find_instrument, key_alter, key_name, letter_of,
    step_to_midi,
)


# --- Pitch ---------------------------------------------------------------

def test_treble_staff_lines():
    # The five lines of the treble staff: E G B D F ("Every Good Boy Does Fine").
    assert step_to_midi(0) == 64  # E4
    assert step_to_midi(2) == 67  # G4
    assert step_to_midi(4) == 71  # B4
    assert step_to_midi(6) == 74  # D5
    assert step_to_midi(8) == 77  # F5


def test_treble_spaces():
    # The four spaces: F A C E.
    assert step_to_midi(1) == 65  # F4
    assert step_to_midi(3) == 69  # A4
    assert step_to_midi(5) == 72  # C5
    assert step_to_midi(7) == 76  # E5


def test_ledger_lines_and_below_middle_c():
    assert step_to_midi(-2) == 60  # middle C
    assert step_to_midi(10) == 81  # A5
    assert step_to_midi(-3) == 59  # B3: crosses down into the octave below


def test_half_steps_between_e_f_and_b_c():
    # Neighboring letters are usually 2 half steps apart, but E-F and B-C are 1.
    assert step_to_midi(1) - step_to_midi(0) == 1  # E4 -> F4
    assert step_to_midi(5) - step_to_midi(4) == 1  # B4 -> C5
    assert step_to_midi(2) - step_to_midi(1) == 2  # F4 -> G4


def test_bass_clef():
    # Bass staff lines: G B D F A ("Good Boys Do Fine Always").
    assert step_to_midi(0, "bass") == 43  # G2
    assert step_to_midi(8, "bass") == 57  # A3
    assert step_to_midi(10, "bass") == 60  # middle C: one ledger line above


def test_note_midi_pitch():
    assert Note(0).midi_pitch() == 64
    assert Note(0).midi_pitch("bass") == 43
    assert Note(None).midi_pitch() is None  # rests have no pitch


# --- Notes and parts -----------------------------------------------------

def test_note_defaults_to_quarter():
    assert Note(4).duration == QUARTER


def test_parts_do_not_share_notes():
    a = Part()
    b = Part()
    a.add_note(Note(0))
    assert len(a.notes) == 1
    assert len(b.notes) == 0


def test_remove_note_and_remove_last():
    part = Part([Note(0), Note(1), Note(2)])
    part.remove_note(1)
    assert [n.step for n in part.notes] == [0, 2]
    part.remove_last()
    assert [n.step for n in part.notes] == [0]
    part.remove_last()
    part.remove_last()  # removing from an empty part must not crash
    assert part.notes == []


def test_insert_note_puts_it_back_in_place():
    part = Part([Note(0), Note(2)])
    part.insert_note(1, Note(1))
    assert [n.step for n in part.notes] == [0, 1, 2]


def test_insert_part_puts_it_back_in_place():
    score = Score()
    score.add_part(find_instrument("Violin"))
    score.add_part(find_instrument("Cello"))
    flute = Part(instrument=find_instrument("Flute"))
    score.insert_part(1, flute)
    assert [p.instrument.name for p in score.parts] == ["Violin", "Flute", "Cello"]


# --- Measures ------------------------------------------------------------

def test_measure_ends_with_exact_measures():
    part = Part([Note(0, WHOLE), Note(0, HALF), Note(0, HALF), Note(0)])
    assert part.measure_ends() == [0, 2]


def test_measure_ends_with_eighths():
    part = Part([Note(0, EIGHTH)] * 8)  # eight eighths = one measure
    assert part.measure_ends() == [7]


def test_measure_ends_when_a_note_overflows():
    # 3 quarters + a half = 5 beats: the bar line goes after the half note.
    # (Ties will handle this properly later; see projectplan.md.)
    part = Part([Note(0), Note(0), Note(0), Note(0, HALF)])
    assert part.measure_ends() == [3]


# --- Sharps, flats, and key signatures -----------------------------------

F4 = 1  # treble-clef step of F4 (the bottom space)
F5 = 8  # treble-clef step of F5 (the top line)
B4 = 4  # the middle line


def test_accidentals_change_the_pitch():
    assert Note(F4).midi_pitch() == 65
    assert Note(F4, alter=SHARP).midi_pitch() == 66
    assert Note(B4, alter=FLAT).midi_pitch() == 70


def test_letter_of():
    assert letter_of(F4, "treble") == 3  # F
    assert letter_of(0, "bass") == 4     # G (bass bottom line)


def test_key_alter():
    assert key_alter(3, 1) == SHARP     # F in G major (1 sharp)
    assert key_alter(0, 1) == NATURAL   # C in G major
    assert key_alter(6, -1) == FLAT     # B in F major (1 flat)
    assert key_alter(2, -2) == FLAT     # E in B-flat major (2 flats)
    assert key_alter(3, 0) == NATURAL   # nothing in C major


def test_key_names():
    assert key_name(0) == "C major / A minor (no ♯ or ♭)"
    assert key_name(1) == "G major / E minor (1♯)"
    assert key_name(-2) == "B♭ major / G minor (2♭)"
    assert len(KEY_NAMES) == 15  # 7 flats ... 7 sharps


def test_each_key_alters_exactly_its_count_of_letters():
    for key in range(-7, 8):
        altered = [letter for letter in range(7) if key_alter(letter, key) != NATURAL]
        assert len(altered) == abs(key)


def signs(notes, key=0, instrument=PIANO):
    return Part(notes, instrument).accidental_signs(key)


def test_naturals_in_c_major_show_no_signs():
    assert signs([Note(0), Note(F4), Note(B4)]) == [None, None, None]


def test_a_sharp_carries_through_the_measure():
    notes = [Note(F4, alter=SHARP), Note(F4, alter=SHARP), Note(F4), Note(0)]
    # 1st F#: sign. 2nd F#: already sharp in this measure, no sign.
    # Then F natural: needs a natural sign to cancel the sharp.
    assert signs(notes) == [SHARP, None, NATURAL, None]


def test_bar_line_resets_accidentals():
    measure_1 = [Note(F4, alter=SHARP), Note(0), Note(0), Note(0)]
    measure_2 = [Note(F4, alter=SHARP)]
    assert signs(measure_1 + measure_2) == [SHARP, None, None, None, SHARP]


def test_accidental_only_affects_its_own_line_or_space():
    # F#4 doesn't change F5 (a different octave, on a different line).
    assert signs([Note(F4, alter=SHARP), Note(F5)]) == [SHARP, None]


def test_key_signature_means_no_sign_needed():
    # G major: F is already sharp, so F# needs no sign, and plain F needs a natural.
    assert signs([Note(F4, alter=SHARP), Note(F5)], key=1) == [None, NATURAL]


def test_rests_never_get_signs():
    assert signs([Note(None), Note(F4, alter=SHARP)]) == [None, SHARP]


def test_overflowing_note_still_resets_at_the_next_measure():
    # 3 quarters + a half note crosses the bar line (beat 5); the next F# is in measure 2.
    notes = [Note(F4, alter=SHARP), Note(0), Note(0), Note(0, HALF), Note(F4, alter=SHARP)]
    assert signs(notes) == [SHARP, None, None, None, SHARP]


# --- Changing clef -------------------------------------------------------

def test_same_clef_means_no_shift():
    assert clef_change_shift([0, 4, 8], "treble", "treble") == 0


def test_clef_change_keeps_letter_names():
    steps = [0, 2, 4, 6, 8]  # E G B D F in treble
    shift = clef_change_shift(steps, "treble", "bass")
    for step in steps:
        old = step_to_midi(step, "treble")
        new = step_to_midi(step + shift, "bass")
        assert (old - new) % 12 == 0  # whole octaves apart: same letter name


def test_clef_change_lands_near_the_middle_of_the_staff():
    steps = [0, 2, 4, 6, 8]  # centered on the middle line in treble
    shift = clef_change_shift(steps, "treble", "bass")
    new_average = sum(s + shift for s in steps) / len(steps)
    assert abs(new_average - 4) <= 3.5  # within half an octave of the middle line


def test_clef_change_there_and_back_returns_home():
    steps = [-2, 3, 10]
    there = clef_change_shift(steps, "treble", "bass")
    moved = [s + there for s in steps]
    back = clef_change_shift(moved, "bass", "treble")
    assert [s + back for s in moved] == steps


# --- Instruments and scores ----------------------------------------------

def test_parts_default_to_piano_in_treble():
    part = Part()
    assert part.instrument == PIANO
    assert part.clef == "treble"


def test_part_clef_comes_from_instrument():
    cello = Part(instrument=find_instrument("Cello"))
    assert cello.clef == "bass"
    # The bottom line of the bass staff is G2.
    cello.add_note(Note(0))
    assert cello.notes[0].midi_pitch(cello.clef) == 43


def test_instrument_list_is_sensible():
    names = [i.name for i in INSTRUMENTS]
    assert len(names) == len(set(names))  # no duplicate names (a set drops repeats)
    for instrument in INSTRUMENTS:
        assert 0 <= instrument.program <= 127
        assert instrument.clef in ("treble", "bass")


def test_find_instrument_unknown_name():
    # pytest.raises checks that the code inside *does* raise this error.
    with pytest.raises(ValueError):
        find_instrument("Kazoo")


def test_score_add_and_remove_parts():
    score = Score()
    violin = score.add_part(find_instrument("Violin"))
    score.add_part(find_instrument("Cello"))
    assert [p.instrument.name for p in score.parts] == ["Violin", "Cello"]
    assert violin is score.parts[0]  # add_part returns the very part it added
    score.remove_part(0)
    assert [p.instrument.name for p in score.parts] == ["Cello"]


# --- Mute and solo -------------------------------------------------------

def make_trio():
    """A helper (not a test: no test_ prefix) that builds a 3-part score."""
    score = Score()
    for name in ["Violin", "Flute", "Cello"]:
        score.add_part(find_instrument(name))
    return score


def audible(score):
    return [score.is_audible(i) for i in range(len(score.parts))]


def test_everyone_plays_by_default():
    assert audible(make_trio()) == [True, True, True]


def test_mute_silences_one_part():
    score = make_trio()
    score.parts[1].muted = True
    assert audible(score) == [True, False, True]


def test_solo_plays_only_soloed_parts():
    score = make_trio()
    score.parts[0].soloed = True
    score.parts[2].soloed = True
    assert audible(score) == [True, False, True]


def test_solo_wins_over_mute():
    score = make_trio()
    score.parts[0].muted = True
    score.parts[0].soloed = True
    assert audible(score) == [True, False, False]


# --- Timeline ------------------------------------------------------------

def test_timeline_merges_parts_in_beat_order():
    score = Score()
    violin = score.add_part(find_instrument("Violin"))
    cello = score.add_part(find_instrument("Cello"))
    violin.notes = [Note(0), Note(1)]   # two quarters: beats 0 and 1
    cello.notes = [Note(0, HALF)]       # one half note: beats 0-2
    starts = [(e.beat, e.part_index, e.note_index) for e in score.timeline() if e.starts]
    assert starts == [(0.0, 0, 0), (0.0, 1, 0), (1.0, 0, 1)]


def test_timeline_pitches_use_each_parts_clef():
    score = Score()
    score.add_part(find_instrument("Violin")).add_note(Note(0))
    score.add_part(find_instrument("Cello")).add_note(Note(0))
    pitches = [e.pitch for e in score.timeline() if e.starts]
    assert pitches == [64, 43]  # E4 in treble, G2 in bass


def test_timeline_ends_come_before_starts_at_the_same_beat():
    score = Score()
    score.add_part(PIANO).notes = [Note(0), Note(0)]  # the same note twice
    kinds = [(e.beat, e.starts) for e in score.timeline()]
    assert kinds == [(0.0, True), (1.0, False), (1.0, True), (2.0, False)]


def test_timeline_includes_rests():
    score = Score()
    score.add_part(PIANO).notes = [Note(None, HALF), Note(0)]
    events = score.timeline()
    assert events[0].pitch is None              # the rest still gets events,
    assert events[-1].beat == 3.0               # so the piece lasts 2 + 1 beats
