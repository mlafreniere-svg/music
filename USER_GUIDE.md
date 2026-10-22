# Music Staff: User Guide

Write music by clicking notes onto a staff, hear it played back, and save, export or print it.

Inside the app, this guide is under **Help ▸ User Guide** (F1); **Help ▸ Keyboard Shortcuts** jumps
straight to the reference table at the end.


## Starting the app

```
cd C:\Users\mason\src\music
.venv\Scripts\Activate.ps1
python main.py
```

A new score opens with one instrument: a piano on a **grand staff** (treble staff for the right hand, bass staff for the left, joined by a brace).


## The window

- **Editing toolbar** (top row): note lengths, Dot, Rest, sharps and flats, Delete Last, Preview.
- **Playback toolbar** (second row): Play, Pause, Stop, Tempo.
- **Score toolbar** (third row): Key, Time, Concert Pitch.
- **Tabs**: one per instrument. The **M** and **S** buttons on each tab are Mute and Solo; the **×** closes the tab. **+ Instrument** (top right) adds one.
- **Title bar**: the file's name, with a `*` when there are unsaved changes.
- **Status bar** (bottom): short hints and messages.


## Writing music

### Placing notes
1. Choose a length: **Whole (1)**, **Half (2)**, **Quarter (3)** or **Eighth (4)**.
2. Click on the staff at the height you want. The note is added at the end of the music, and you hear it (turn **Preview** off for silence).

Notes always go at the end; the staff grows and scrolls sideways as you write.

### Dotted notes
Turn on **Dot (.)** to make half and quarter notes 1½ times as long (a dotted half lasts 3 beats). Dot is grayed out for whole and eighth notes.

### Rests
Turn on **Rest (R)**: clicks add rests of the chosen length instead of notes. Press R again to go back to notes.

### Sharps and flats
The **Key / ♮ / ♯ / ♭** buttons decide the accidental of the next notes you place:
- **Key (K)**, the default: follow the key signature (in G major, an F becomes F♯).
- **♮ (N)**, **♯ (S)**, **♭ (F)**: force natural, sharp or flat.

To change a note already on the staff, point at it and press **+** (raise a half step: ♭ → ♮ → ♯) or **-** (the minus key: lower).

Signs are shown the way printed music does it: a sharp carries through the rest of its measure, and a ♮ appears when one is needed to cancel it.

### Chords
- **Shift+click** above or below a note to add that pitch to it.
- **Shift+click** a head in a chord to remove just that head.

Dragging and + / - work on the single head under the mouse.

### Changing and deleting notes
- **Drag** a note up or down to change its pitch (the pointer becomes a hand over a note).
- **Right-click** a note to delete it.
- **Backspace** (or **Delete Last**) deletes the last note. On a grand staff, it acts on the staff you last clicked.

### Undo
**Ctrl+Z** undoes the last change (notes, drags, chords, tabs, tempo, key, time); **Ctrl+Y** redoes it. The **Edit** menu names what will be undone, e.g. "Undo Move note".

### Ties and bar lines
Bar lines are drawn automatically from the time signature. A note too long for what's left of its measure is written as tied notes across the bar line. It still sounds as one note.


## Instruments

### Adding, changing and closing
- **+ Instrument** adds a tab. Instruments are grouped: keyboards on a grand staff, treble clef, transposing instruments, bass clef, and percussion.
- **Right-click a tab** to change its instrument. The music keeps its sound; notes move by octaves to sit well on the new staff. A grand-staff tab can switch only between keyboards (piano, organ, harp, marimba).
- **×** on a tab closes it (undoable). A score always keeps at least one instrument. Up to 14 instruments.

### Grand staff
Keyboard instruments get two staves: the right hand (treble) above and the left hand (bass) below. Each hand has its own rhythm; notes played together line up vertically.

### Transposing instruments
Guitars, bass guitar, double bass, B♭ trumpet and clarinet, horn in F, and alto and tenor sax are *written* at a different pitch than they *sound*, as on real printed parts. Each shows its own key signature. Playback uses the sounding pitch. See **Concert Pitch** below to view them at sounding pitch.

### Drum Kit
On a drum staff, each line or space is a drum, not a pitch. Point at the staff to see which drum is at that height in the status bar. Clicks snap to the nearest drum. Cymbals have × note heads. Shift+click to hit two drums at once (e.g. kick + hi-hat).

| Position on the staff | Drum |
|---|---|
| above the staff (ledger line) | Crash cymbal |
| space above the top line | Hi-hat |
| top line | Ride cymbal |
| fourth space | High tom |
| fourth line | Mid tom |
| third space | Snare drum |
| second space | Floor tom |
| bottom space | Kick (bass drum) |
| below the staff | Hi-hat pedal |

### Mute and Solo
- **M** (Mute) silences that instrument; its staff turns gray.
- **S** (Solo) plays only the soloed instruments.

They change what you hear, not the music, so they aren't saved.


## The whole piece (Score toolbar)

- **Key**: the key signature, from 7 flats to 7 sharps. Notes keep their pitches; only the signs change.
- **Time**: the time signature (2/4, 3/4, 4/4, 5/4, 6/8, 9/8, 12/8, 2/2). Notes keep their lengths; bar lines and ties move.
- **Concert Pitch**: show transposing instruments at the pitch they sound instead of as written. A view setting only; it isn't saved.

Key and Time are undoable and saved with the file.


## Playback

- **Play** (or **Space**) plays every instrument together. A blue band follows the notes on each staff.
- **Pause** (or **Space** again) stops where you are; **Resume** continues from there.
- **Stop** (**Esc**) stops and goes back to the beginning.
- **Tempo**: the slider sets beats (quarter notes) per minute. It's saved with the piece.


## Songs from an AI

An AI chat (for example Google AI Mode) can arrange a song for you, as a file the app opens directly.

1. **Help ▸ Copy AI Translation Guide.** This copies instructions that explain the app to the AI:
   its file format, instruments and limits.
2. In the AI chat, **paste**, then type the song's name after `SONG REQUEST:` (add wishes if you
   like, e.g. "jazzy, with saxophone"). Send it.
3. **Copy the AI's whole reply.**
4. In the app: **File ▸ Paste Song from AI** (Ctrl+Shift+V), paste, and click **Open Song**.
5. The song opens as a new, unsaved song. A message shows the AI's notes (what it simplified) and any
   small fixes the app made. **Save** it (Ctrl+S) to keep it.

If the app finds problems it can't fix, it lists them instead of opening the song. Click
**Copy for the AI**, paste that into the chat, and the AI will send a corrected file; paste that the
same way.

Keep in mind: the AI writes the song from memory, so less famous songs may not be quite right; it may
decline some copyrighted songs; and very long songs are shortened to their best-known part (64
measures at most).


## Files

| Menu item | Key | What it does |
|---|---|---|
| File ▸ New | Ctrl+N | Start a new score (asks first if there are unsaved changes). |
| File ▸ Open | Ctrl+O | Open a saved score (`.music.json`). |
| File ▸ Save | Ctrl+S | Save. The first time, it asks for a name. |
| File ▸ Save As | Ctrl+Shift+S | Save under a new name. |
| File ▸ Export MIDI | Ctrl+E | A `.mid` file that MuseScore, a DAW, or any music program can open. |
| File ▸ Print to PDF | Ctrl+P | Every instrument's music on US Letter pages, ready to print. |
| File ▸ Paste Song from AI | Ctrl+Shift+V | Open a song from an AI's reply (see "Songs from an AI"). |
| Help ▸ Copy AI Translation Guide | | Copy the instructions to give an AI along with a song name. |

Files are saved in the `saved_music` folder by default. Songs, MIDI files and PDFs are never added to git.

If you close the app or open another file with unsaved changes, it asks: **Save**, **Don't Save** or **Cancel**.


## Keyboard and mouse reference

| Key or action | What it does |
|---|---|
| `1` `2` `3` `4` | Whole / half / quarter / eighth notes |
| `.` | Dot on/off (half and quarter notes) |
| `R` | Rest mode on/off |
| `K` `N` `S` `F` | Next notes: follow key / natural / sharp / flat |
| Click the staff | Add a note (or rest) at the end |
| Shift+click near a note | Add that pitch to the note (chord) |
| Shift+click a chord head | Remove that head |
| Drag a note | Change its pitch |
| Point at a note, `+` or `=` | Raise it a half step |
| Point at a note, `-` | Lower it a half step |
| Right-click a note | Delete it |
| `Backspace` | Delete the last note |
| Right-click a tab | Change its instrument |
| `Space` | Play / pause |
| `Esc` | Stop |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `Ctrl+N` `Ctrl+O` `Ctrl+S` | New / Open / Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+E` | Export MIDI |
| `Ctrl+P` | Print to PDF |
| `Ctrl+Shift+V` | Paste a song from an AI |
| `F1` | This guide |
| `Alt+F` `Alt+E` `Alt+V` `Alt+H` | File / Edit / View / Help menus |


## Not supported yet

- Sixteenth notes, and dotted eighths (which need sixteenths)
- Changing the time signature partway through a piece
- Printing a full score (all instruments on each line); the PDF prints each instrument in turn
- Double sharps and double flats
- Inserting a note in the middle of the music (notes are added at the end; drag or delete to edit)
