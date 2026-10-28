# Acceptance Tests for the Phase 2 Change Requests

ENGG\*4450, Group 10. SCRUM-79 (SCRUM-115, SCRUM-116, SCRUM-117). Author: Chizorom Anyalechi. Updated October 27, 2026, to match the merged fixes (PR #2 and PR #3).

These tests are written for someone with no developer help. Follow Part A once, then run Part B and Part C. Each test checks one flow from `use-cases.md`. Record the actual result, pass or fail, your name and the date for every test.

## Part A: Setting up a fresh copy (SCRUM-115)

You need Python 3.10 to 3.14 and Git. Check with `python --version` and `git --version`. On Windows, try `py --version` if `python` is not recognized. Part C must be run on macOS, Linux or WSL.

**A1. Get the code.** Replace `<release-tag>` with the tag from SCRUM-81. Until that exists, use `main`.

```
git clone https://github.com/uoguelph-engg4450/F26-Group10-beets.git
cd F26-Group10-beets
git checkout <release-tag>
```

**A2. Create an isolated environment and install.**

Windows (PowerShell):

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

macOS, Linux or WSL:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows, use the standard Python from python.org (the `py` launcher comes with it). If `python -m venv` creates `.venv\bin` instead of `.venv\Scripts`, that Python is an MSYS2 or MinGW build, and `pip install` will fail while building `jellyfish`. In that case delete `.venv` and recreate it with `py -m venv .venv`.

Before running `pip install`, check that your prompt starts with `(.venv)`. If it does not, the environment is not active and beets would be installed into your main Python instead. The `-e` flag installs our group's copy of the code, not the public release. If PowerShell refuses to run the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

**A3. Use a separate test library.** Create a folder named `acceptance` inside the repository, and in it a file named `config.yaml` containing:

```
directory: music
library: library.db
```

These paths are read relative to the `acceptance` folder. Then point beets at it. Repeat this in every new terminal window.

```
Windows (PowerShell):    $env:BEETSDIR = "$PWD\acceptance"
macOS, Linux or WSL:     export BEETSDIR="$PWD/acceptance"
```

**A4. Check the install.**

| Command | Expected result |
|---|---|
| `beet version` | Prints `beets version 2.14.1`, the Python version and `plugins: musicbrainz`, with no errors. The first run also prints several `Created database backup at: ...` lines while beets sets up the new library. These are normal and only appear once. |
| `beet config -p` | Shows the path to `acceptance/config.yaml`. |

To start over at any time, delete `acceptance/library.db` and the `acceptance/music` folder.

## Part B: Genre regular expressions on tracks with several genres (UC-1, #6961)

### B0. Setup for all Part B tests

The sample songs all share the same title and artist, so first tell beets to keep them all instead of asking about duplicates. Add these two lines to `acceptance/config.yaml` (the second line is indented four spaces):

```
import:
    duplicate_action: keep
```

Then run these from the repository folder. In Windows PowerShell and in macOS or Linux shells, keep the single quotes exactly as shown.

```
beet import -A -s test/rsrc/full.mp3
beet import -A -s test/rsrc/full.flac
beet import -A -s test/rsrc/date.mp3
beet modify -y id:1 'genres=Electro; House'
beet modify -y id:2 'genres=Electro'
beet modify -y id:3 'genres=Electro House'
beet ls -f '$id: $genres'
```

`-A` imports without looking songs up online, and `-s` imports each file as a single track. The last command should print:

```
1: Electro; House
2: Electro
3: Electro House
```

Track 1 has two genres, track 2 has one, and track 3 has one genre that only contains the word Electro. If the output differs, stop and report it before running the tests.

### Tests

| ID | Covers | Steps | Expected result |
|---|---|---|---|
| AT-1.1 | Main flow | `beet ls -f '$id: $genres' 'genres::^Electro$'` | Lists tracks **1 and 2**, and not track 3. Before the fix, only track 2 is listed. |
| AT-1.2 | Main flow, second genre | `beet ls -f '$id: $genres' 'genres::^House$'` | Lists track **1** only. Before the fix, nothing is listed. |
| AT-1.3 | Alternate 3b, unanchored | `beet ls -f '$id: $genres' 'genres::Electro'` | Lists tracks **1, 2 and 3**, the same as before the fix. |
| AT-1.4 | Alternate 4a, no match | `beet ls -f '$id: $genres' 'genres::^Techno$'` | Prints nothing and returns to the prompt with no error. |
| AT-1.5 | Error E1, invalid expression | `beet ls 'genres::['` | Prints one line starting `invalid query:` that says `'['` is not a regular expression. No traceback. |

## Part C: Private login token files (UC-2, #6984)

Run on macOS, Linux or WSL only. These tests need internet access. On WSL, work on a copy of the repository inside your Linux home folder (for example `~/beets-test`), not under `/mnt/c/...`. Files on the Windows drive do not show real Linux permissions, so the permission checks would give wrong results.

### C0. Setup for all Part C tests

1. Complete Part A, including `BEETSDIR`.
2. Add this line to `acceptance/config.yaml`:

   ```
   plugins: spotify
   ```

3. If you did not run Part B, import one track so the library is not empty (needed for AT-2.6):

   ```
   beet import -A -s test/rsrc/full.mp3
   ```

4. Make sure no token file exists yet:

   ```
   rm -f acceptance/spotify_token.json
   ```

### Tests

| ID | Covers | Steps | Expected result |
|---|---|---|---|
| AT-2.1 | Main flow | 1. `beet version`<br>2. `ls -l acceptance/spotify_token.json` | Step 1 prints the version with no errors. Step 2 shows the file with permissions `-rw-------`. Before the fix, it shows `-rw-r--r--`. |
| AT-2.2 | Alternate 2a, token reused | 1. Complete AT-2.1.<br>2. `ls -l --time-style=full-iso acceptance/spotify_token.json` (on macOS use `ls -lT`), and note the time.<br>3. `beet version`<br>4. Repeat step 2. | Step 3 runs with no errors. In step 4 the permissions are still `-rw-------` and the time has not changed, showing the saved token was reused. |
| AT-2.3 | Alternate 4a, loose default permissions | 1. `rm -f acceptance/spotify_token.json`<br>2. `(umask 000; beet version)`<br>3. `ls -l acceptance/spotify_token.json` | The file is still `-rw-------`. Before the fix, it is `-rw-rw-rw-`. |
| AT-2.4 | Error E1, rejected login | 1. `rm -f acceptance/spotify_token.json`<br>2. Add `spotify:` and, indented under it, `client_secret: wrong` to `acceptance/config.yaml`.<br>3. `beet version`<br>4. `ls acceptance/spotify_token.json`<br>5. Remove the two lines added in step 2. | Step 3 prints a warning starting `** error loading plugin spotify`, followed by beets' standard plugin error details, ending with `Spotify authorization failed: 400 Client Error ... Invalid client secret`. It then still prints the version. Step 4 reports that the file does not exist. |
| AT-2.5 | Main flow step 5, token kept out of debug output | 1. `rm -f acceptance/spotify_token.json`<br>2. `beet -v version > acceptance/debug.log 2>&1`<br>3. `TOKEN=$(python -c "import json; print(json.load(open('acceptance/spotify_token.json'))['access_token'])")`<br>4. `grep -c -F "$TOKEN" acceptance/debug.log` | Step 2 prints nothing to the screen (the output goes to the log file). Step 4 prints `0`: the new token appears nowhere in the debug output. Before the fix, it prints `1`, because the debug output included a line `Spotify access token: ...`. |
| AT-2.6 | Alternate 2b, expired token saved before the fix | 1. `echo '{"access_token": "expired"}' > acceptance/spotify_token.json`<br>2. `chmod 644 acceptance/spotify_token.json`<br>3. `beet spotify`<br>4. `ls -l acceptance/spotify_token.json`<br>5. `cat acceptance/spotify_token.json` | Step 3 finishes without a traceback (it may list tracks it did or did not find on Spotify). Step 4 shows `-rw-------`. Step 5 shows a new token instead of `expired`, proving the file was re-saved. Before the fix, step 4 still shows `-rw-r--r--`. |

## Results log

| Test | Tester | Date | Actual result | Pass or fail |
|---|---|---|---|---|
| AT-1.1 | Chizorom Anyalechi | 2026-10-27 | Listed tracks 1 and 2 | Pass |
| AT-1.2 | Chizorom Anyalechi | 2026-10-27 | Listed track 1 | Pass |
| AT-1.3 | Chizorom Anyalechi | 2026-10-27 | Listed tracks 1, 2 and 3 | Pass |
| AT-1.4 | Chizorom Anyalechi | 2026-10-27 | Printed nothing, no error | Pass |
| AT-1.5 | Chizorom Anyalechi | 2026-10-27 | `invalid query: 'genres::[': '[' is not a regular expression: unterminated character set at position 0`, no traceback | Pass |
| AT-2.1 | Chizorom Anyalechi | 2026-10-27 | Version printed; token file `-rw-------` | Pass |
| AT-2.2 | Chizorom Anyalechi | 2026-10-27 | `600`, modification time unchanged after second run | Pass |
| AT-2.3 | Chizorom Anyalechi | 2026-10-27 | `-rw-------` with umask 000 | Pass |
| AT-2.4 | Chizorom Anyalechi | 2026-10-27 | Plugin load error ending `Spotify authorization failed ... Invalid client secret`; version still printed; no token file | Pass |
| AT-2.5 | Chizorom Anyalechi | 2026-10-27 | `0` (token not in debug log) | Pass |
| AT-2.6 | Chizorom Anyalechi | 2026-10-27 | `-rw-------`; file holds a new token instead of `expired` | Pass |

Part B was run on Windows 11 (PowerShell, Python 3.11). Part C was run on Ubuntu under WSL, on a fresh copy in the Linux home folder.
