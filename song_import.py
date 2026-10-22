"""Reading a song file out of an AI's reply (see translation_plan.md).

An AI's reply is rarely *just* the file: there's usually a sentence before
or after it, ``` marks around it, and sometimes small mistakes. This module:

1. finds the JSON inside the pasted text,
2. checks every part of it against what the app can do,
3. fixes what's safe to fix (and lists each fix), and
4. explains real problems in plain words, so they can be sent back to the AI.

Everything here is plain logic (no windows), so it's easy to test.
"""

import difflib
import json
import re
from dataclasses import dataclass, field

from model import (
    DRUM_MAP, HIGHEST_FILE_STEP, INSTRUMENTS, KEY_NAMES, LOWEST_FILE_STEP, MAX_PARTS,
    TIME_SIGNATURES, find_instrument, measure_length, nearest_drum_step, split_duration,
)
from storage import (
    FORMAT_NAME, FORMAT_VERSION, score_from_dict, time_signature_from_value, time_signature_to_text,
)

MIN_TEMPO, MAX_TEMPO = 40, 200
MAX_PROBLEMS_PER_PART = 8  # beyond this, a part's problems are summarized


@dataclass
class ImportResult:
    score: object = None  # the Score, or None if it couldn't be opened
    fixes: list = field(default_factory=list)     # safe changes that were made
    problems: list = field(default_factory=list)  # reasons it couldn't be opened
    ai_notes: str = ""    # the AI's own note about what it simplified

    @property
    def ok(self):
        return self.score is not None


def import_song(text):
    """Find, check, fix and load the song file in pasted text."""
    result = ImportResult()
    data = read_json(text, result)
    if data is None:
        return result
    check_and_fix(data, result)
    if result.problems:
        return result
    try:
        result.score = score_from_dict(data)  # the app's own loader has the last word
    except (KeyError, TypeError, ValueError) as error:
        result.problems.append(f"The file couldn't be loaded: {error}")
    return result


# --- Step 1: finding the JSON ------------------------------------------------

def find_json_text(text):
    """The JSON part of a pasted reply, or None.

    Prefers a ``` code block; otherwise takes everything from the first {
    to the last }.
    """
    for block in re.findall(r"```[a-zA-Z]*\s*\n(.*?)```", text, re.S):  # re.S: . matches newlines too
        if "{" in block:
            return block
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        return None
    return text[start:end + 1]


def strip_comments(text):
    """Remove // comments, but not // inside quoted text (like "https://...").

    Walks through the text one character at a time, remembering whether it's
    inside a "string". A simple search-and-replace couldn't tell the difference.
    """
    out = []
    in_string = False
    i = 0
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\":           # a backslash escapes the next character (like \")
                out.append(text[i + 1:i + 2])
                i += 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            out.append(char)
        elif text.startswith("//", i):  # a comment: skip to the end of the line
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
            continue
        else:
            out.append(char)
        i += 1
    return "".join(out)


def tidy_json(text):
    """Fix common slips AIs make that JSON doesn't allow. Returns (text, what was fixed)."""
    fixed = []
    if any(quote in text for quote in "“”‘’"):
        text = (text.replace("“", '"').replace("”", '"')
                    .replace("‘", "'").replace("’", "'"))
        fixed.append("Replaced curly quotes with straight ones.")
    without_comments = strip_comments(text)
    if without_comments != text:
        text = without_comments
        fixed.append("Removed comments (JSON doesn't allow them).")
    without_commas = re.sub(r",(\s*[}\]])", r"\1", text)  # a comma right before } or ]
    if without_commas != text:
        text = without_commas
        fixed.append("Removed extra commas before closing brackets.")
    # A key with nothing after its colon, like "time_signature":, (an AI chat
    # may drop something it took for a citation). Read it as null: "missing".
    filled = re.sub(r'("\s*:\s*)(?=[,}\]])', r"\1null", text)
    if filled != text:
        text = filled
        fixed.append("A value was empty (nothing after the colon); treated it as missing.")
    return text, fixed


def read_json(text, result):
    """Parse the JSON in `text`, fixing small slips; None if impossible."""
    json_text = find_json_text(text)
    if json_text is None:
        result.problems.append(
            "No song file was found in the pasted text. Paste the AI's whole reply, "
            "including the part between the { and } brackets.")
        return None
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        tidied, fixed = tidy_json(json_text)
        try:
            data = json.loads(tidied)
            result.fixes.extend(fixed)
        except json.JSONDecodeError as error:
            result.problems.append(
                f"The file isn't valid JSON (line {error.lineno}, column {error.colno}): "
                f"{error.msg}.")
            return None
    if not isinstance(data, dict):  # isinstance: is it this kind of thing?
        result.problems.append("The file should be one JSON object, starting with {.")
        return None
    return data


# --- Step 2: checking and fixing ---------------------------------------------

def check_and_fix(data, result):
    """Check the whole file; fix what's safe, record problems for the rest."""
    check_header(data, result)
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts:
        result.problems.append('The file has no "parts" (the list of instruments).')
        return
    if len(parts) > MAX_PARTS:
        result.problems.append(f"The file has {len(parts)} parts; the app allows at most {MAX_PARTS}.")
        return
    for number, part in enumerate(parts, start=1):  # start=1: count from 1, like people do
        check_part(number, part, result)
    if not result.problems:
        even_out_lengths(data, result)
    notes = data.pop("ai_notes", "")  # take the AI's note out of the data
    result.ai_notes = notes if isinstance(notes, str) else " ".join(map(str, notes))


def check_header(data, result):
    fmt = data.get("format")
    if fmt is None:
        result.fixes.append(f'Added the missing "format" ("{FORMAT_NAME}").')
    elif fmt != FORMAT_NAME:
        # e.g. "Music Staff": the app's name instead of the exact value. The
        # rest of the file is checked anyway, so this is safe to correct.
        result.fixes.append(f'Corrected "format" from {json.dumps(fmt)} to "{FORMAT_NAME}".')
    data["format"] = FORMAT_NAME

    version = data.get("version")
    if version is None:
        result.fixes.append(f'Added the missing "version" ({FORMAT_VERSION}).')
    elif not isinstance(version, int) or version > FORMAT_VERSION:
        result.problems.append(
            f'"version" is {json.dumps(version)}; this app reads versions up to {FORMAT_VERSION}.')
    data["version"] = FORMAT_VERSION  # after checking, the layout is the current one

    tempo = data.get("tempo_bpm")
    if tempo is None:
        result.fixes.append('Added the missing "tempo_bpm" (100).')
        data["tempo_bpm"] = 100
    elif not isinstance(tempo, (int, float)):
        result.problems.append(f'"tempo_bpm" should be a number, not {json.dumps(tempo)}.')
    else:
        clamped = max(MIN_TEMPO, min(MAX_TEMPO, round(tempo)))
        if clamped != tempo:
            result.fixes.append(f"Changed the tempo from {tempo} to {clamped} "
                                f"(the app plays {MIN_TEMPO} to {MAX_TEMPO}).")
        data["tempo_bpm"] = clamped

    key = data.get("key")
    if key is None:
        result.fixes.append('Added the missing "key" (0, C major).')
        data["key"] = 0
    elif key not in KEY_NAMES:
        result.problems.append(f'"key" should be a number from -7 to 7, not {json.dumps(key)}.')

    time = data.get("time_signature")
    if time is None:
        result.fixes.append('Added the missing "time_signature" (4/4).')
        data["time_signature"] = "4/4"
        return
    try:
        signature = time_signature_from_value(time)  # "3/4" or [3, 4]
    except (ValueError, TypeError):
        signature = None
    if signature not in TIME_SIGNATURES:
        allowed = ", ".join(f'"{t}/{b}"' for t, b in TIME_SIGNATURES)
        result.problems.append(f'"time_signature" {json.dumps(time)} isn\'t supported. Use one of: {allowed}.')
    else:
        data["time_signature"] = time_signature_to_text(signature)


def match_instrument(name):
    """The app's instrument for a name: exact, or a close match. None if unknown."""
    names = [instrument.name for instrument in INSTRUMENTS]
    if name in names:
        return name
    for known in names:
        if known.lower() == name.lower():
            return known
    # "Trumpet in Bb" is close to "Trumpet in B♭": difflib measures how alike strings are.
    flat_spelled = {known.replace("♭", "b"): known for known in names}
    if name in flat_spelled:
        return flat_spelled[name]
    close = difflib.get_close_matches(name, names, n=1, cutoff=0.8)
    return close[0] if close else None


def check_part(number, part, result):
    if not isinstance(part, dict):
        result.problems.append(f"Part {number} should be an object with an \"instrument\" and \"notes\".")
        return
    name = part.get("instrument")
    label = f'Part {number} ("{name}")'
    if not isinstance(name, str):
        result.problems.append(f'Part {number} has no "instrument" name.')
        return
    matched = match_instrument(name)
    if matched is None:
        result.problems.append(
            f'{label}: the app has no instrument called "{name}". Use a name from the guide\'s '
            "instrument table, exactly as written.")
        return
    if matched != name:
        result.fixes.append(f'{label}: used the instrument "{matched}".')
        part["instrument"] = matched
        label = f'Part {number} ("{matched}")'
    instrument = find_instrument(matched)

    if not isinstance(part.get("notes"), list):
        result.problems.append(f'{label} has no "notes" list.')
        return
    if instrument.grand:
        if "lower_notes" not in part:
            part["lower_notes"] = []
            result.fixes.append(f"{label}: gave the left hand (lower_notes) an empty part.")
        elif not isinstance(part["lower_notes"], list):
            result.problems.append(f'{label}: "lower_notes" should be a list of notes.')
            return
    elif "lower_notes" in part:
        result.problems.append(
            f'{label} has "lower_notes", but only grand-staff instruments have a left hand. '
            'Use "Piano (grand staff)" (or another grand-staff keyboard), or a separate part.')
        return

    problems = []
    staves = [("notes", part["notes"])]
    if instrument.grand:
        staves.append(("lower_notes", part["lower_notes"]))
    for key, notes in staves:
        hand = " (left hand)" if key == "lower_notes" else ""
        if not instrument.is_drums:
            clef = "bass" if key == "lower_notes" else instrument.clef
            fix_ranges(notes, clef, f"{label}{hand}", result)
        for index, note in enumerate(notes, start=1):
            check_note(note, instrument, f"{label}{hand}, note {index}", problems, result)
    if len(problems) > MAX_PROBLEMS_PER_PART:
        extra = len(problems) - MAX_PROBLEMS_PER_PART
        problems = problems[:MAX_PROBLEMS_PER_PART] + [f"{label}: ...and {extra} more like these."]
    result.problems.extend(problems)


def head_slots(notes):
    """Every pitched head in a staff's notes, as (note, chord index or None),
    so each can be read and changed in place. Skips anything malformed
    (check_note reports that)."""
    slots = []
    for note in notes:
        if not isinstance(note, dict) or not is_step(note.get("step")):
            continue
        slots.append((note, None))
        for i, head in enumerate(note.get("chord", []) if isinstance(note.get("chord"), list) else []):
            if isinstance(head, list) and len(head) == 2 and is_step(head[0]):
                slots.append((note, i))
    return slots


def is_step(value):
    return isinstance(value, int) and not isinstance(value, bool)  # (True counts as an int in Python)


def get_step(slot):
    note, i = slot
    return note["step"] if i is None else note["chord"][i][0]


def set_step(slot, step):
    note, i = slot
    if i is None:
        note["step"] = step
    else:
        note["chord"][i][0] = step


def fix_ranges(notes, clef, label, result):
    """Bring notes outside the staff's range back in, keeping their sound where possible."""
    slots = head_slots(notes)
    steps = [get_step(slot) for slot in slots]
    in_range = lambda s: LOWEST_FILE_STEP <= s <= HIGHEST_FILE_STEP
    if not steps or all(in_range(s) for s in steps):
        return
    # The most common mistake: a bass-clef staff written with the treble-clef
    # table. On a bass staff, steps below the range are lower than C2, below
    # where any bass part is written, so that's almost certainly what happened.
    # The same pitch sits 12 steps higher on a bass staff than on a treble
    # staff: move the whole staff by +12, then fix any leftovers by octaves.
    if clef == "bass" and min(steps) < LOWEST_FILE_STEP:
        for slot in slots:
            set_step(slot, get_step(slot) + 12)
        result.fixes.append(f"{label}: the notes looked like treble-clef steps on a bass-clef "
                            "staff; moved them to the matching bass-clef steps (same pitches).")
        if all(in_range(get_step(slot)) for slot in slots):
            return
    moved = 0
    for slot in slots:
        step = get_step(slot)
        while step < LOWEST_FILE_STEP:
            step += 7  # up an octave: same letter name
        while step > HIGHEST_FILE_STEP:
            step -= 7
        if step != get_step(slot):
            set_step(slot, step)
            moved += 1
    result.fixes.append(f"{label}: moved {moved} note(s) by an octave to fit the staff.")


def check_note(note, instrument, where, problems, result):
    """Check one note; fix it in place where safe."""
    if not isinstance(note, dict):
        problems.append(f"{where}: each note should look like {{\"step\": 0, \"duration\": 1.0, \"alter\": 0}}.")
        return
    duration = note.get("duration")
    if not isinstance(duration, (int, float)) or duration <= 0:
        problems.append(f"{where}: \"duration\" should be a number of beats, like 1.0, not {json.dumps(duration)}.")
    elif (duration * 2) != int(duration * 2):  # not a whole number of eighth notes
        problems.append(f"{where}: a duration of {duration} beats isn't supported "
                        "(the shortest note is an eighth, 0.5). Use eighths or longer.")
    note.setdefault("alter", 0)  # setdefault: add it only if it's missing
    step = note.get("step")
    if step is None:  # a rest
        note["alter"] = 0
        note.pop("chord", None)
        return
    heads = [(step, note["alter"])] + [tuple(h) if isinstance(h, list) else h for h in note.get("chord", [])]
    cleaned = []
    for head in heads:
        if not (isinstance(head, tuple) and len(head) == 2):
            problems.append(f"{where}: each chord pitch should be a pair like [2, 0], not {json.dumps(head)}.")
            return
        head_step, alter = head
        if not isinstance(head_step, int) or isinstance(head_step, bool):
            problems.append(f"{where}: \"step\" should be a number from the pitch table "
                            f"(like 0 for E4 in treble), not {json.dumps(head_step)}.")
            return
        if instrument.is_drums:
            if head_step not in DRUM_MAP:
                snapped = nearest_drum_step(head_step)
                result.fixes.append(f"{where}: moved drum step {head_step} to the nearest drum, "
                                    f"{DRUM_MAP[snapped].name} (step {snapped}).")
                head_step = snapped
            alter = 0
        elif not LOWEST_FILE_STEP <= head_step <= HIGHEST_FILE_STEP:
            problems.append(f"{where}: step {head_step} is outside the staff's range "
                            f"({LOWEST_FILE_STEP} to {HIGHEST_FILE_STEP}). Move it by an octave (7 steps).")
            return
        if alter not in (-1, 0, 1):
            problems.append(f"{where}: \"alter\" should be -1 (flat), 0 or 1 (sharp), not {json.dumps(alter)}.")
            return
        if any(head_step == s for s, _ in cleaned):
            result.fixes.append(f"{where}: removed a repeated pitch from the chord.")
            continue
        cleaned.append((head_step, alter))
    note["step"], note["alter"] = cleaned[0]
    if len(cleaned) > 1:
        note["chord"] = [list(head) for head in cleaned[1:]]
    else:
        note.pop("chord", None)


def even_out_lengths(data, result):
    """Pad every part (and left hand) with rests to the same whole number of measures."""
    measure = measure_length(time_signature_from_value(data["time_signature"]))
    staves = []  # (description, list of notes)
    for number, part in enumerate(data["parts"], start=1):
        label = f'Part {number} ("{part["instrument"]}")'
        staves.append((label, part["notes"]))
        if "lower_notes" in part:
            staves.append((f"{label} (left hand)", part["lower_notes"]))
    longest = max(sum(n["duration"] for n in notes) for _, notes in staves)
    target = -(-longest // measure) * measure  # round *up* to whole measures (-(-a // b) is a ceiling)
    for label, notes in staves:
        total = sum(n["duration"] for n in notes)
        missing = target - total
        if missing > 0:
            for length in split_duration(missing):
                notes.append({"step": None, "duration": length, "alter": 0})
            if total == longest:
                result.fixes.append(f"{label}: filled the last measure with rests.")
            else:
                result.fixes.append(f"{label}: was {missing:g} beats shorter than the longest part; "
                                    "added rests at the end.")


# --- Step 3: a message for the AI ---------------------------------------------

def message_for_ai(result):
    """Text to paste back to the AI so it can send a corrected file."""
    lines = ["The Music Staff app couldn't open your file. Please fix these problems and send the "
             "complete corrected file, following the translation guide:", ""]
    lines += [f"- {problem}" for problem in result.problems]
    return "\n".join(lines)
