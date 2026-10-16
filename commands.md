# Command reference

All the commands used in this project, grouped by topic. Run them in PowerShell
(Windows Terminal, or VS Code's terminal: Ctrl+`).

Inside Claude Code, put `!` in front of a command to run it yourself, for example `! git status`.


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
| `exit()` | Leave the interactive `>>>` Python prompt. |

`-m` must be written with no space (`-m`, not `- m`).


## Running this project

| Command | What it does |
|---|---|
| `python play_note.py` | Sound test: plays middle C. |
| `python main.py` | Run the music staff app. |


## Git (version control)

| Command | What it does |
|---|---|
| `git status` | Show what has changed: `M` = modified, `??` = new/untracked. |
| `git diff` | Show the exact lines changed since the last commit. |
| `git add <files>` | Stage changes for the next commit. |
| `git commit -m "message"` | Save the staged changes as a snapshot. |
| `git push` | Upload your commits to GitHub. |
| `git log --oneline` | List past commits, one per line. |
| `git show <id>` | Show what a specific commit changed. |

The usual cycle: edit files, then `git status`, `git add ...`, `git commit -m "..."`, `git push`.

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
