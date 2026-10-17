"""Saving and loading scores as JSON files.

JSON is a plain-text format built from the same pieces as Python data:
dictionaries ({"key": value}), lists ([1, 2]), strings, numbers, true/false,
and null (Python's None). So saving works in two steps:

    Score  --score_to_dict-->  dicts and lists  --json.dump-->  text file

and loading does the same in reverse. Keeping the steps separate means the
conversion can be tested without touching any files.
"""

import json
from pathlib import Path

from model import COMMON_TIME, Note, Part, Score, find_instrument

FILE_EXTENSION = ".music.json"
FORMAT_NAME = "music-staff"  # identifies our files among all JSON files
FORMAT_VERSION = 5           # bump this if the layout of the file ever changes
# Version history:
#   1  tempo, parts, notes (step + duration)
#   2  adds each note's "alter" (sharp/flat) and the score's "key" signature.
#      Version 1 files still load: their notes are natural, in C major.
#   3  adds "lower_notes" for grand-staff parts (the left hand).
#      Older files have no grand staffs, so they load unchanged.
#   4  adds the "time_signature", e.g. [3, 4]. Older files are in 4/4.
#   5  adds "chord" to notes that have extra pitches: [[step, alter], ...].
READABLE_VERSIONS = (1, 2, 3, 4, 5)


def note_to_dict(note):
    data = {"step": note.step, "duration": note.duration, "alter": note.alter}
    if note.chord:  # only chords get the extra key, so single notes stay short
        data["chord"] = [list(head) for head in note.chord]
    return data


def notes_to_list(notes):
    """Notes as plain dicts, ready for JSON."""
    return [note_to_dict(n) for n in notes]


def notes_from_list(items):
    """The reverse of notes_to_list. Missing "alter" (version 1 files) means
    natural; missing "chord" means a single note."""
    return [
        Note(item["step"], item["duration"], item.get("alter", 0),
             [tuple(head) for head in item.get("chord", [])])  # JSON lists back to tuples
        for item in items
    ]


def score_to_dict(score):
    """Turn a Score into plain dicts and lists that JSON can store."""
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "tempo_bpm": score.tempo_bpm,
        "key": score.key,
        "time_signature": list(score.time_signature),  # JSON has lists, not tuples
        "parts": [part_to_dict(part) for part in score.parts],
    }


def part_to_dict(part):
    """One part as a dict. Mute/Solo are deliberately not saved: every file
    opens with all parts audible."""
    data = {
        # Save the instrument by name; its program and clef come from the
        # INSTRUMENTS list when the file is loaded.
        "instrument": part.instrument.name,
        "notes": notes_to_list(part.notes),
    }
    if part.lower is not None:
        data["lower_notes"] = notes_to_list(part.lower.notes)  # the grand staff's left hand
    return data


def score_from_dict(data):
    """Rebuild a Score from the dicts and lists made by score_to_dict.

    Raises ValueError if the data isn't one of our files.
    """
    if data.get("format") != FORMAT_NAME:  # .get returns None if the key is missing
        raise ValueError("This isn't a Music Staff file.")
    if data.get("version") not in READABLE_VERSIONS:
        raise ValueError(f"Unsupported file version: {data.get('version')}")

    # .get(key, default) gives the default when the key is missing, which is
    # how version 1 files (no key, no alter) still load.
    score = Score(
        tempo_bpm=data["tempo_bpm"],
        key=data.get("key", 0),
        # tuple(...) turns the saved list [3, 4] back into (3, 4).
        time_signature=tuple(data.get("time_signature", COMMON_TIME)),
    )
    for part_data in data["parts"]:
        part = Part(instrument=find_instrument(part_data["instrument"]))  # grand: makes .lower
        part.notes = notes_from_list(part_data["notes"])
        if part.lower is not None:
            part.lower.notes = notes_from_list(part_data.get("lower_notes", []))
        score.parts.append(part)
    return score


def save_score(score, path):
    """Write a score to a file."""
    # "with" opens the file and makes sure it's closed again afterwards,
    # even if something goes wrong while writing.
    with open(path, "w", encoding="utf-8") as file:
        json.dump(score_to_dict(score), file, indent=2)  # indent=2: easy to read
        file.write("\n")


def load_score(path):
    """Read a score from a file.

    Raises OSError if the file can't be read, and ValueError if it isn't a
    valid Music Staff file (json's own errors are a kind of ValueError).
    """
    with open(path, encoding="utf-8") as file:
        data = json.load(file)
    try:
        return score_from_dict(data)
    except (KeyError, TypeError, AttributeError) as error:
        # A missing key or a wrong type means the file is damaged.
        # "raise ... from error" keeps the original error attached for debugging.
        raise ValueError(f"The file is damaged: {error!r}") from error


def display_name(path):
    """The file's name without folders or extension, for the title bar."""
    name = Path(path).name
    if name.endswith(FILE_EXTENSION):
        return name[: -len(FILE_EXTENSION)]  # slice off the extension
    return Path(path).stem
