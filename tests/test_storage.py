"""Tests for storage.py: saving and loading scores.

Tests that take a `tmp_path` parameter get a fresh, empty temporary folder
from pytest, so they can write files without cluttering the project.
"""

import json

import pytest

from model import HALF, WHOLE, Note, Score, find_instrument
from storage import display_name, load_score, save_score, score_from_dict, score_to_dict


def make_duet():
    """A small score with two instruments, a rest, and a non-default tempo."""
    score = Score(tempo_bpm=132)
    violin = score.add_part(find_instrument("Violin"))
    violin.notes = [Note(0), Note(None, HALF), Note(10)]
    cello = score.add_part(find_instrument("Cello"))
    cello.notes = [Note(-2, WHOLE)]
    return score


def test_save_then_load_gives_back_the_same_score(tmp_path):
    original = make_duet()
    path = tmp_path / "duet.music.json"  # / joins paths, like folders in a file path
    save_score(original, path)
    loaded = load_score(path)
    # Dataclasses compare field by field, so == checks every part and note.
    assert loaded == original


def test_file_is_readable_json(tmp_path):
    path = tmp_path / "duet.music.json"
    save_score(make_duet(), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["tempo_bpm"] == 132
    assert data["parts"][0]["instrument"] == "Violin"
    assert data["parts"][0]["notes"][1] == {"step": None, "duration": 2.0, "alter": 0}  # the rest


def test_sharps_flats_and_key_are_saved(tmp_path):
    score = make_duet()
    score.key = -2                    # B-flat major
    score.parts[0].notes[0].alter = 1  # a sharp
    path = tmp_path / "keys.music.json"
    save_score(score, path)
    loaded = load_score(path)
    assert loaded.key == -2
    assert loaded.parts[0].notes[0].alter == 1
    assert loaded == score


def test_version_1_files_still_load():
    # A file saved before sharps and flats existed: no "key", no "alter".
    old = {
        "format": "music-staff",
        "version": 1,
        "tempo_bpm": 90,
        "parts": [{"instrument": "Flute", "notes": [{"step": 3, "duration": 1.0}]}],
    }
    score = score_from_dict(old)
    assert score.key == 0
    assert score.parts[0].notes[0].alter == 0
    assert score.parts[0].notes[0].step == 3


def test_grand_staff_left_hand_is_saved(tmp_path):
    score = Score()
    piano = score.add_part(find_instrument("Piano (grand staff)"))
    piano.notes = [Note(0)]
    piano.lower.notes = [Note(4, HALF), Note(None)]
    path = tmp_path / "piano.music.json"
    save_score(score, path)
    loaded = load_score(path)
    assert loaded.parts[0].lower.notes == piano.lower.notes
    assert loaded == score


def test_version_2_files_still_load():
    old = {
        "format": "music-staff", "version": 2, "tempo_bpm": 100, "key": 1,
        "parts": [{"instrument": "Piano", "notes": [{"step": 1, "duration": 1.0, "alter": 1}]}],
    }
    score = score_from_dict(old)
    assert score.parts[0].lower is None  # an old single-staff piano stays single-staff
    assert score.parts[0].notes[0].alter == 1


def test_time_signature_is_saved(tmp_path):
    score = make_duet()
    score.time_signature = (6, 8)
    path = tmp_path / "waltz.music.json"
    save_score(score, path)
    loaded = load_score(path)
    assert loaded.time_signature == (6, 8)  # a tuple again, so the scores compare equal
    assert loaded == score


def test_older_files_are_in_four_four():
    data = score_to_dict(make_duet())
    del data["time_signature"]
    data["version"] = 3
    assert score_from_dict(data).time_signature == (4, 4)


def test_future_versions_are_rejected():
    data = score_to_dict(make_duet())
    data["version"] = 99
    with pytest.raises(ValueError):
        score_from_dict(data)


def test_mute_and_solo_are_not_saved():
    score = make_duet()
    score.parts[0].muted = True
    score.parts[1].soloed = True
    loaded = score_from_dict(score_to_dict(score))  # no file needed for this one
    assert not loaded.parts[0].muted
    assert not loaded.parts[1].soloed


def test_other_json_files_are_rejected():
    with pytest.raises(ValueError):
        score_from_dict({"name": "some other program's file"})


def test_damaged_file_is_rejected(tmp_path):
    path = tmp_path / "damaged.music.json"
    data = score_to_dict(make_duet())
    del data["parts"][0]["notes"]  # break it
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_score(path)


def test_not_json_at_all_is_rejected(tmp_path):
    path = tmp_path / "notes.music.json"
    path.write_text("this is not JSON", encoding="utf-8")
    with pytest.raises(ValueError):
        load_score(path)


def test_unknown_instrument_is_rejected():
    data = score_to_dict(make_duet())
    data["parts"][0]["instrument"] = "Kazoo"
    with pytest.raises(ValueError):
        score_from_dict(data)


def test_display_name():
    assert display_name(r"C:\Users\mason\Music\Hot Cross Buns.music.json") == "Hot Cross Buns"
    assert display_name("song.json") == "song"
