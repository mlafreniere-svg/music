# Command reference

All the commands used in this project, grouped by topic. Run them in PowerShell
(Windows Terminal, or VS Code's terminal: Ctrl+`).

Inside Claude Code, put `!` in front of a command to run it yourself, for example `! git status`.
Only use `!` for commands; messages to Claude go without it.


## Two shells: PowerShell and Git Bash

A shell is the program that reads the commands you type. This project uses two:

- **PowerShell** is Windows' own shell, used in Windows Terminal and VS Code. Everything in this file is written for PowerShell unless it says otherwise.
- **Git Bash** is a Linux-style shell that comes with Git. Claude Code's `!` commands currently run in Git Bash (errors start with `/usr/bin/bash`).

Git and Python commands work the same in both. The differences:

| | PowerShell | Git Bash |
|---|---|---|
| Paths | `C:\Program Files\GitHub CLI\gh.exe` | `"/c/Program Files/GitHub CLI/gh.exe"` |
| Activate venv | `.venv\Scripts\Activate.ps1` | `source .venv/Scripts/activate` |
| PATH commands (`$env:Path ...`) | work | don't work |

Run a program by its full path (when it isn't found on PATH), in Git Bash:
```
"/c/Program Files/GitHub CLI/gh.exe" repo view --web
```
The quotes are needed because of the space in "Program Files".


## Daily routine

```
cd C:\Users\mason\src\music      # go to the project folder
.venv\Scripts\Activate.ps1       # activate the virtual environment; (.venv) appears in the prompt
code .                           # open the project in VS Code (optional)
python main.py                   # run the app
```


## PowerShell basics

| Command | What it does |
|---|---|
| `pwd` | Show the folder you are in ("print working directory"). |
| `dir` or `ls` | List the files in the current folder. |
| `cd <folder>` | Move into a folder, e.g. `cd C:\Users\mason\src\music`. |
| `cd ..` | Go up one folder. |
| `cd ~` | Go to your home folder (`C:\Users\mason`). |
| `mkdir <name>` | Make a new folder. |
| `cls` | Clear the screen. |
| `exit` | Close the terminal. |
| `notepad <file>` | Open a file in Notepad, e.g. `notepad main.py`. |
| `code .` | Open the current folder in VS Code. |

Keyboard shortcuts:
- **Tab** completes file and folder names as you type them.
- **Up arrow** brings back your previous commands.
- **Ctrl+C** stops a running command.

Relative paths (like `main.py` or `.venv\Scripts\...`) are looked up starting from the current folder.
If a command says a file doesn't exist, check your folder with `pwd`.


## PATH and environment

| Command | What it does |
|---|---|
| `$env:Path -split ';'` | List every folder on PATH, one per line. |
| `$env:Path -split ';' \| Select-String fluidsynth` | Check whether a specific folder is on PATH. |
| `[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path','User') + ';<folder>', 'User')` | Permanently add a folder to your user PATH (used once, for FluidSynth). |
| `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')` | Reload PATH in the current terminal, without reopening it. |
| `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` | Allow local scripts such as `Activate.ps1` to run (used once). |

PATH changes only show up in terminals opened afterward. If a program you just installed
"is not recognized", close the terminal app completely and reopen it.


## Installing software (winget)

| Command | What it does |
|---|---|
| `winget search <name>` | Search for a program. |
| `winget install --id <id> -e` | Install a program by its exact ID. |
| `winget list --id <id>` | Check whether a program is installed. |

Used in this project:
```
winget install --id Python.Python.3.12 -e
winget install --id Microsoft.VisualStudioCode -e
winget install --id Git.Git -e
winget install --id GitHub.cli -e
```

Downloading and unzipping (used for FluidSynth, which isn't in winget):
```
Invoke-WebRequest <url> -OutFile <file>    # download a file
Expand-Archive <zip> <folder>              # unzip it
```


## Python and the virtual environment

| Command | What it does |
|---|---|
| `python --version` | Show which Python version runs. |
| `python -m venv .venv` | Create a virtual environment in `.venv` (once per project). |
| `.venv\Scripts\Activate.ps1` | Activate it. `python` and `pip` now use the project's copy. |
| `deactivate` | Turn it off again. |
| `python -m pip install <package>` | Install a package into the active environment. |
| `python -m pip install -r requirements.txt` | Install every package listed in `requirements.txt`. |
| `python -m pip list` | Show the installed packages. |
| `python <file>.py` | Run a Python program. |
| `python` | Start the interactive `>>>` prompt: type Python one line at a time and see results immediately. Good for trying things out, e.g. `from model import Note`. |
| `exit()` | Leave the interactive `>>>` Python prompt. |

`-m` must be written with no space (`-m`, not `- m`).


## Running this project

| Command | What it does |
|---|---|
| `python play_note.py` | Sound test: plays middle C. |
| `python main.py` | Run the music staff app. |

Keyboard shortcuts inside the app:

| Key | What it does |
|---|---|
| `1` `2` `3` `4` | Choose whole / half / quarter / eighth. |
| `R` | Turn rest mode on/off (clicks add rests of the chosen duration). |
| `Backspace` | Delete the last note. |
| `Space` | Play the staff from the beginning. |
| Right-click a note | Delete that note. |


## Testing (pytest)

| Command | What it does |
|---|---|
| `python -m pip install pytest` | Install pytest, the testing tool (once). |
| `python -m pytest` | Run every test in `tests\`. One dot per passing test, `F` for a failure. |
| `python -m pytest -v` | The same, listing each test by name (`-v` = verbose). |

Tests live in `tests\test_*.py`. Each `test_` function is one test; `assert` means "this must be true".
Use `python -m pytest` (not plain `pytest`) so the tests can find `model.py`.
Run the tests after every change. If something fails, pytest shows the failing line and the values involved.


## Git (version control)

| Command | What it does |
|---|---|
| `git status` | Show what has changed: `M` = modified, `??` = new/untracked. |
| `git diff` | Show the exact lines changed since the last commit. `-` = removed, `+` = added. |
| `git diff <file>` | The same, for one file only. |
| `git add <files>` | Stage changes for the next commit. List the files by name (safest). |
| `git add .` | Stage every changed file in the folder (quicker; check `git status` first). |
| `git add --dry-run .` | Show what `git add .` *would* stage, without staging anything. |
| `git commit -m "message"` | Save the staged changes as a snapshot. |
| `git commit --amend -m "message"` | ⚠️ Replace the most recent commit, e.g. to fix a typo in its message. **Only before `git push`.** |
| `git push` | Upload your commits to GitHub. |
| `git log --oneline` | List past commits, one per line. |
| `git show <id>` | Show what a specific commit changed. |
| `git restore <file>` | ⚠️ Throw away uncommitted changes to a file and go back to the last commit. Can't be undone. |
| `git ls-files --eol` | Show each file's line endings (`lf`/`crlf`) in git (`i/`) and on disk (`w/`). |

The usual cycle: edit files, then `git status`, `git diff`, `git add ...`, `git commit -m "..."`, `git push`.

Reading the output:
- `git status`: files under "Changes to be committed" are staged; "Untracked files" are new to git.
- `git commit`: `[main fc006a6]` is the new commit's ID; "3 files changed, 291 insertions(+)" counts lines.
- `git push`: `6f9ae55..fc006a6 main -> main` means GitHub moved from the old commit to the new one.
- `git status` saying "ahead of 'origin/main' by 1 commit" means there's a commit that isn't pushed yet.

In VS Code, the **Source Control** icon on the left (a branching line) does the same thing with buttons:
type a message, then click **Commit** and **Sync/Push**.

### Branches

A **branch** is a separate line of commits, so a fix can be worked on without touching `main` until it's ready.

| Command | What it does |
|---|---|
| `git branch` | List your branches; `*` marks the one you're on. |
| `git switch -c <name>` | Create a new branch from where you are, and move to it. Note the space before `-c`. |
| `git switch <name>` | Move to an existing branch, e.g. `git switch main`. |
| `git merge <name>` | Bring another branch's commits into the branch you're on. |
| `git branch -d <name>` | Delete a branch after it has been merged (its commits stay in `main`). |
| `git commit -m "title" -m "more"` | Each extra `-m` adds a paragraph to the message, e.g. `-m "Fixes #1"`. |

Branch names like `fix/1-quiet-playback` say the kind of work, the issue number, and a short description.

The branch cycle: `git switch -c fix/...`, edit and commit, then `git switch main`, `git merge fix/...`, `git push`, `git branch -d fix/...`.

Special files:
- `.gitignore` lists files git should never track (`.venv`, SoundFonts).
- `.gitattributes` sets how git treats files. Here it keeps LF line endings, so the "LF will be replaced by CRLF" warnings stop.

Used once to set up:
```
git init -b main                                   # turn a folder into a git repository
git config --global user.name "<name>"             # your name on commits
git config --global user.email "<email>"           # your email on commits
```


## GitHub CLI (gh)

| Command | What it does |
|---|---|
| `gh auth login --web` | Log in to GitHub through your browser. |
| `gh auth status` | Check whether you're logged in. |
| `gh repo create <name> --private --source . --push` | Create a GitHub repository from this folder and upload it. |
| `gh repo view --web` | Open this project's GitHub page in your browser. |
| `gh issue create --title "..." --body "..."` | Open a new issue (a bug or task to track). `--body-file <file>` reads a longer description from a file. |
| `gh issue list` | List the open issues. |
| `gh issue view <number>` | Show one issue, e.g. `gh issue view 1`. Add `--web` to open it in the browser. |
| `gh issue close <number>` | Close an issue by hand. |

**Issues** are GitHub's to-do list for bugs and ideas, numbered #1, #2, …
Putting `Fixes #1` in a commit message closes issue #1 automatically when that commit is pushed.


## Errors we've hit and their fixes

| Error | Fix |
|---|---|
| `'python' / 'pip' / 'git' is not recognized` | The terminal was opened before the install. Reopen the terminal app. |
| `running scripts is disabled on this system` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `can't open file 'C:\Users\mason\play_note.py'` | Wrong folder: `cd C:\Users\mason\src\music` first. |
| `ModuleNotFoundError: No module named ...` | The venv isn't active: `.venv\Scripts\Activate.ps1` |
| `Couldn't find the FluidSynth library` | FluidSynth's `bin` folder isn't on PATH in this terminal. Reopen the terminal. |
| A `>>>` prompt appears unexpectedly | A typo in the command (e.g. `- m`). Type `exit()`. |
| `fluidsynth: error: not enough MIDI in devices found` | Harmless: there's no MIDI keyboard plugged in. |
| `git add` → `Nothing specified, nothing added.` | Tell it which files: `git add <files>` or `git add .` |
| `commit: command not found` | Git commands start with `git`: `git commit ...`. (And to upload commits, use `git push`.) |
| `fatal: pathspec 'status' did not match any files` | Two commands got combined (`git add status`). Git read `status` as a file name. Run `git status` and `git add <files>` separately. |
| `git: 'switch-c' is not a git command` | A missing space: `git switch -c <name>`. |
| `warning: ... LF will be replaced by CRLF` | Harmless. Fixed for good by `.gitattributes`. |
| `/usr/bin/bash: ... unexpected EOF while looking for matching` | A message to Claude was sent with `!` and ran as a command. Leave off the `!`. |
| `/usr/bin/bash: line 1: gh: command not found` | Claude Code started before gh was on PATH. Use the full path (see "Two shells"), or restart Claude Code. |
