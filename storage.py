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

from model import Note, Part, Score, find_instrument

FILE_EXTENSION = ".music.json"
FORMAT_NAME = "music-staff"  # identifies our files among all JSON files
FORMAT_VERSION = 1           # bump this if the layout of the file ever changes


def score_to_dict(score):
    """Turn a Score into plain dicts and lists that JSON can store."""
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "tempo_bpm": score.tempo_bpm,
        "parts": [
            {
                # Save the instrument by name; its program and clef come
                # from the INSTRUMENTS list when the file is loaded.
                "instrument": part.instrument.name,
                "notes": [
                    {"step": note.step, "duration": note.duration}
                    for note in part.notes
                ],
                # Mute/Solo are deliberately not saved: every file opens
                # with all parts audible.
            }
            for part in score.parts
        ],
    }


def score_from_dict(data):
    """Rebuild a Score from the dicts and lists made by score_to_dict.

    Raises ValueError if the data isn't one of our files.
    """
    if data.get("format") != FORMAT_NAME:  # .get returns None if the key is missing
        raise ValueError("This isn't a Music Staff file.")
    if data.get("version") != FORMAT_VERSION:
        raise ValueError(f"Unsupported file version: {data.get('version')}")

    score = Score(tempo_bpm=data["tempo_bpm"])
    for part_data in data["parts"]:
        part = Part(instrument=find_instrument(part_data["instrument"]))
        for note_data in part_data["notes"]:
            part.add_note(Note(note_data["step"], note_data["duration"]))
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
