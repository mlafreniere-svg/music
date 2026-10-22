"""Tests for song_import.py: reading a song file out of an AI's reply."""

import copy
import json

from song_import import import_song, message_for_ai
from translation_guide import example_data, file_text


def reply(data, before="Here is your song!", after="Enjoy playing it."):
    """An AI-style reply: chatter, then the file in a ```json block, then more chatter."""
    return f"{before}\n\n```json\n{file_text(data)}\n```\n\n{after}"


def changed(**edits):
    """The guide's example with some changes made. edits: a function per name, applied in order."""
    data = copy.deepcopy(example_data())  # deepcopy: a full copy, so changes don't leak between tests
    for edit in edits.values():
        edit(data)
    return data


# --- Finding the file ------------------------------------------------------

def test_the_guides_own_example_imports_cleanly():
    result = import_song(reply(example_data()))
    assert result.ok
    assert result.fixes == [] and result.problems == []
    assert "trumpet" in result.ai_notes
    assert [p.instrument.name for p in result.score.parts] == ["Piano (grand staff)", "Trumpet in B♭", "Drum Kit"]


def test_file_without_code_fences_is_found():
    text = "Sure! " + json.dumps(example_data()) + " Hope that helps."
    assert import_song(text).ok


def test_no_file_at_all():
    result = import_song("Sorry, I can't help with that song.")
    assert not result.ok
    assert "No song file was found" in result.problems[0]


def test_broken_json_reports_where():
    result = import_song('```json\n{"format": "music-staff", "parts": [\n```')
    assert not result.ok
    assert "line" in result.problems[0]


def test_comment_marks_inside_text_are_kept():
    data = changed(a=lambda d: d.update(ai_notes="Based on https://example.com/song"))
    text = reply(data).replace('"key": 0,', '"key": 0, // C major')  # needs tidying
    result = import_song(text)
    assert result.ok
    assert result.ai_notes == "Based on https://example.com/song"  # the // in the address survived


def test_common_json_slips_are_fixed():
    text = reply(example_data()).replace('"key": 0,', '"key": 0, // C major').replace(
        '"tempo_bpm": 100', '“tempo_bpm”: 100')
    text = text.replace('"Drum Kit",', '"Drum Kit",\n      // drums\n')
    text = text.replace("]\n    }\n  ]", "],\n    }\n  ]")  # a trailing comma
    result = import_song(text)
    assert result.ok, result.problems
    assert any("curly quotes" in fix for fix in result.fixes)
    assert any("extra commas" in fix for fix in result.fixes)


# --- Safe fixes ------------------------------------------------------------

def test_missing_header_values_are_added():
    def strip(data):
        for key in ("format", "version", "tempo_bpm", "key", "time_signature"):
            del data[key]
    result = import_song(reply(changed(a=strip)))
    assert result.ok
    assert len(result.fixes) == 5
    assert result.score.time_signature == (4, 4)


def test_tempo_is_clamped():
    result = import_song(reply(changed(a=lambda d: d.update(tempo_bpm=300))))
    assert result.ok and result.score.tempo_bpm == 200
    assert "300" in result.fixes[0]


def test_close_instrument_names_are_matched():
    def rename(data):
        data["parts"][0]["instrument"] = "piano (Grand Staff)"
        data["parts"][1]["instrument"] = "Trumpet in Bb"
    result = import_song(reply(changed(a=rename)))
    assert result.ok
    assert result.score.parts[1].instrument.name == "Trumpet in B♭"
    assert len(result.fixes) == 2


def test_grand_staff_without_left_hand_gets_an_empty_one():
    def drop(data):
        del data["parts"][0]["lower_notes"]
    result = import_song(reply(changed(a=drop)))
    assert result.ok
    assert sum(n.duration for n in result.score.parts[0].lower.notes) == 16  # padded with rests


def test_drum_steps_snap_to_the_nearest_drum():
    result = import_song(reply(changed(a=lambda d: d["parts"][2]["notes"][1].update(step=4))))
    assert result.ok
    assert result.score.parts[2].notes[1].step in (3, 5)
    assert any("nearest drum" in fix for fix in result.fixes)


def test_repeated_chord_pitch_is_removed():
    def repeat(data):
        data["parts"][0]["lower_notes"][0]["chord"].append([3, 0])  # same as the main pitch
    result = import_song(reply(changed(a=repeat)))
    assert result.ok
    assert result.score.parts[0].lower.notes[0].chord == [(5, 0), (7, 0)]


def test_short_parts_are_padded_to_whole_measures():
    def shorten(data):
        del data["parts"][1]["notes"][-1]             # trumpet: 2 beats short
        data["parts"][2]["notes"].append(               # drums: 1 beat into a new measure
            {"step": 9, "duration": 1.0, "alter": 0})
    result = import_song(reply(changed(a=shorten)))
    assert result.ok
    lengths = {sum(n.duration for n in staff.notes) for p in result.score.parts for staff in p.staves()}
    assert lengths == {20.0}  # everyone padded out to 5 whole measures


# --- Problems: the song isn't opened ----------------------------------------

def problem_for(edit):
    result = import_song(reply(changed(a=edit)))
    assert not result.ok
    return " ".join(result.problems)


def test_unknown_instrument():
    assert "no instrument called" in problem_for(lambda d: d["parts"][1].update(instrument="Kazoo"))


def test_sixteenth_notes():
    assert "isn't supported" in problem_for(lambda d: d["parts"][1]["notes"][0].update(duration=0.25))


def test_note_names_instead_of_steps():
    assert "pitch table" in problem_for(lambda d: d["parts"][1]["notes"][0].update(step="E4"))


def test_notes_off_the_staff_move_by_octaves():
    result = import_song(reply(changed(a=lambda d: d["parts"][1]["notes"][0].update(step=20))))
    assert result.ok
    assert result.score.parts[1].notes[0].step == 6  # 20 - 7 - 7: same letter, two octaves down
    assert any("by an octave" in fix for fix in result.fixes)


def test_bass_staff_written_with_treble_steps_is_corrected():
    # A real AI mistake (see translation_plan.md): a G-B-D chord and a G bass
    # note written with the *treble* table on bass-clef staves.
    def treble_steps_on_bass(data):
        data["parts"][0]["lower_notes"] = [
            {"step": -5, "duration": 4.0, "alter": 0, "chord": [[-3, 0], [-1, 0]]}] * 4
        data["parts"].append({"instrument": "Bass Guitar", "notes": [
            {"step": -5, "duration": 1.0, "alter": 0}] * 16})
    result = import_song(reply(changed(a=treble_steps_on_bass)))
    assert result.ok, result.problems
    left_hand = result.score.parts[0].lower.notes[0]
    assert left_hand.heads == [(7, 0), (9, 0), (11, 0)]        # G3 B3 D4 in bass clef: same pitches
    assert result.score.parts[3].notes[0].step == 7             # the bass guitar's G
    assert sum("treble-clef steps" in fix for fix in result.fixes) == 2


def test_the_reply_from_the_first_real_trial():
    # The same kinds of slips as the first Google AI Mode reply, in a made-up tune.
    text = """{
      "format": "Music Staff",
      "version": 1,
      "tempo_bpm": 148,
      "key": -1,
      "time_signature":,
      "parts": [
        {"instrument": "Piano (grand staff)",
         "notes": [{"step": -2, "duration": 4.0, "alter": 0}],
         "lower_notes": [{"step": -6, "duration": 4.0, "alter": 0, "chord": [[-4, 0], [-2, 0]]}]},
        {"instrument": "Bass Guitar", "notes": [{"step": -6, "duration": 4.0, "alter": 0}]}
      ],
      "ai_notes": ["Simplified the rhythm."]
    }"""
    result = import_song(text)
    assert result.ok, result.problems
    assert result.score.time_signature == (4, 4)
    assert result.ai_notes == "Simplified the rhythm."
    assert result.score.parts[1].notes[0].step == 6  # F: treble step -6 -> bass step 6


def test_treble_steps_on_a_bass_staff_with_high_notes_too():
    # The left hand of the first real trial: low chords AND a C-E-G chord
    # written at treble steps -2, 0, 2. After +12 the G (14) is too high, so it
    # moves down an octave, keeping every chord's notes (C E G stays C E G).
    def left_hand(data):
        data["parts"][0]["lower_notes"] = [
            {"step": -5, "duration": 8.0, "alter": 0, "chord": [[-3, 0], [-1, 0]]},  # G B D
            {"step": -2, "duration": 8.0, "alter": 0, "chord": [[0, 0], [2, 0]]}]    # C E G
    result = import_song(reply(changed(a=left_hand)))
    assert result.ok, result.problems
    first, second = result.score.parts[0].lower.notes
    assert first.heads == [(7, 0), (9, 0), (11, 0)]   # G3 B3 D4
    assert second.heads == [(10, 0), (12, 0), (7, 0)]  # C4 E4, and G3 (moved down an octave)


def test_double_sharp():
    assert '"alter"' in problem_for(lambda d: d["parts"][1]["notes"][0].update(alter=2))


def test_unsupported_time_signature():
    assert "isn't supported" in problem_for(lambda d: d.update(time_signature="7/8"))


def test_time_signature_in_brackets_is_still_read():
    result = import_song(reply(changed(a=lambda d: d.update(time_signature=[3, 4]))))
    assert result.ok and result.score.time_signature == (3, 4)


def test_left_hand_on_a_one_staff_instrument():
    assert "only grand-staff" in problem_for(lambda d: d["parts"][1].update(lower_notes=[]))


def test_too_many_parts():
    assert "at most" in problem_for(lambda d: d.update(parts=d["parts"] * 5))


def test_newer_file_version():
    assert "versions up to" in problem_for(lambda d: d.update(version=99))


def test_many_problems_are_summarized():
    def break_all(data):
        for note in data["parts"][1]["notes"]:
            note["duration"] = 0.25
    text = problem_for(break_all)
    assert "more like these" in text


def test_message_for_the_ai_lists_the_problems():
    result = import_song(reply(changed(a=lambda d: d["parts"][1].update(instrument="Kazoo"))))
    message = message_for_ai(result)
    assert "corrected file" in message and "Kazoo" in message
