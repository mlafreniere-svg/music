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
    assert data["parts"][0]["notes"][1] == {"step": None, "duration": 2.0}  # the rest


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
