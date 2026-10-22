"""Tests for translation_guide.py: the AI translation guide must be correct,
complete, and up to date, since an AI follows it literally."""

import json
import re

from model import DRUM_MAP, INSTRUMENTS, MAX_PARTS, step_to_midi
from storage import FORMAT_VERSION, score_from_dict
from translation_guide import GUIDE_FILE, build_guide, example_data, file_text, pitch_name


def test_guide_names_every_instrument():
    guide = build_guide()
    for instrument in INSTRUMENTS:
        assert f"`{instrument.name}`" in guide


def test_pitch_tables_match_the_app():
    guide = build_guide()
    treble = guide.split("### Treble-clef staves")[1].split("### Bass-clef staves")[0]
    bass = guide.split("### Bass-clef staves")[1].split("## Instruments")[0]
    # Spot checks a musician would know: middle C is step -2 in treble, step 10 in bass.
    assert "| C4 | -2 | ledger line |" in treble
    assert "| C4 | 10 | ledger line |" in bass
    assert "| E4 | 0 | bottom line |" in treble and "| G2 | 0 | bottom line |" in bass
    # And every row of each table agrees with the app's own conversion.
    for clef, table in (("treble", treble), ("bass", bass)):
        rows = re.findall(r"^\| ([A-G]\d) \| (-?\d+) \|", table, re.M)
        assert len(rows) == 17
        for name, step in rows:
            assert pitch_name(step_to_midi(int(step), clef)) == name


def test_guide_warns_about_using_the_wrong_clef_table():
    guide = build_guide()
    assert "G3 is step -5 in treble clef but step 7 in bass clef" in guide
    assert "`lower_notes` (left hand)" in guide.split("### Bass-clef staves")[1]


def test_drum_table_matches_the_app():
    guide = build_guide()
    for step, drum in DRUM_MAP.items():
        assert f"| {step} | {drum.name} |" in guide


def test_guide_states_current_limits():
    guide = build_guide()
    assert f'Exactly `{FORMAT_VERSION}`' in guide
    assert '"4/4"' in guide  # time signatures as text (see storage.py, version 6)
    assert f"1 to {MAX_PARTS}" in guide


def test_example_in_the_guide_loads():
    guide = build_guide()
    # The example is the only ```json block in the guide.
    block = re.search(r"```json\n(.*?)\n```", guide, re.S).group(1)
    data = json.loads(block)
    score = score_from_dict(data)
    assert len(score.parts) == 3
    # Every part, and the piano's left hand, last the same number of beats.
    lengths = {sum(n.duration for n in staff.notes) for p in score.parts for staff in p.staves()}
    assert lengths == {16.0}


def test_file_text_is_the_same_json():
    data = example_data()
    assert json.loads(file_text(data)) == data  # the hand-made layout is still exactly the data


def test_guide_file_is_up_to_date():
    # If this fails: run   python translation_guide.py   to rewrite AI_TRANSLATION_GUIDE.md.
    assert GUIDE_FILE.read_text(encoding="utf-8") == build_guide()
