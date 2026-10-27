# Use Case Descriptions for the Phase 2 Change Requests

ENGG\*4450, Group 10. SCRUM-74 (SCRUM-98, SCRUM-99). Author: Chizorom Anyalechi. Updated October 27, 2026, to match the merged fixes.

These descriptions cover the two items selected in SCRUM-75. Each acceptance test in `acceptance-tests.md` checks one flow from these descriptions.

## UC-1: Find tracks by an exact genre when tracks have several genres

| | |
|---|---|
| **GitHub issue** | [beetbox/beets#6961](https://github.com/beetbox/beets/issues/6961). Jira: SCRUM-76. Implemented by Ali Meski in PR #2. |
| **Primary actor** | Beets user |
| **Secondary actor** | None. The query runs only against the local library database. |
| **Goal** | List every track that has a given genre, even when that track also has other genres. |
| **Preconditions** | Beets is installed and the library contains tracks. At least one track has more than one genre, for example `Electro` and `House`. |
| **Trigger** | The user runs a list command with a regular expression query on the `genres` field, for example `beet ls 'genres::^Electro$'`. |

**Main flow**

1. The user runs `beet ls` with a regular expression query on `genres`, anchored with `^` and `$` to match one whole genre.
2. Beets compiles the regular expression.
3. Beets checks the expression against each genre of each track separately.
4. Beets lists every track that has at least one genre matching the expression, including tracks with more than one genre.

**Alternate flows**

- **3a. The track has only one genre.** Beets checks that single genre, as it did before the fix.
- **3b. The expression is not anchored** (for example `genres::Electro`). Beets lists every track where any genre contains the text, as before.
- **4a. No track matches.** Beets prints nothing and returns to the prompt without an error.

**Error flows**

- **E1. The expression is invalid** (for example `genres::[`). Beets does not run the query. It prints an error naming the query and saying it is not a regular expression, with no crash or traceback.

**Postconditions**

- The list contains exactly the tracks that have a genre matching the expression.
- Tracks whose genres only contain the text as part of a longer value (for example `Electro House` for `^Electro$`) are not listed.
- The library is not changed.

**Notes**

- Cause found in the code: multiple genres are stored as one string joined by a hidden separator (`beets/dbcore/types.py`, `DelimitedString`), and the `regexp` database function (`beets/dbcore/db.py`) runs the expression against that whole string. An anchored expression therefore fails whenever a track has a second genre.
- Confirmed by the implementer (PR #2): `regexp()` now splits the stored value on the multi-value separator and matches each value separately.
- The fix applies to every multi-valued field, not only `genres` (for example `artists` and `composers`). Single-value fields behave exactly as before.

## UC-2: Keep a metadata source login token private

| | |
|---|---|
| **GitHub issue** | [beetbox/beets#6984](https://github.com/beetbox/beets/issues/6984). Jira: SCRUM-77. Implemented by Khaleed Jimoh in PR #3. |
| **Primary actor** | Beets user on a computer shared with other user accounts |
| **Secondary actors** | The online metadata service (Spotify in the tests) and the operating system's file system |
| **Goal** | When beets saves a login token for an online service, only the user who owns it can read the token file, and the token never appears in beets' debug output. |
| **Preconditions** | Beets is installed on macOS or Linux. The Spotify or Beatport plugin is enabled (Spotify in the tests). The computer has internet access. No token file exists yet. |
| **Trigger** | The user runs any beets command, which loads the plugin and makes it log in to the service. |

**Main flow**

1. The user runs a beets command.
2. The plugin finds no saved token and requests a new one from the service.
3. The service returns a token.
4. Beets writes the token to the plugin's token file in the beets configuration folder, readable and writable only by the owner (permissions `600`, shown as `-rw-------`).
5. Beets does not print the token, even when run with `-v` for debug output.
6. The command finishes normally.

**Alternate flows**

- **2a. A token file already exists.** The plugin reads the saved token and skips steps 3 and 4. The file and its permissions are unchanged.
- **2b. A saved token has expired.** The service rejects it, the plugin requests a new token, and beets saves it over the old file. If the old file was readable by others (for example one saved before the fix), beets tightens it to `600`.
- **4a. The user's default file permissions are looser than usual** (for example `umask 000`). Beets still creates the token file as owner-only.

**Error flows**

- **E1. The service rejects the request.** Beets prints a warning that the plugin could not load because authorization failed, carries on with the command without that plugin, and writes no token file.

**Postconditions**

- The token file exists with owner-only permissions (`600`).
- Other user accounts on the same computer cannot read the token.
- The token does not appear in any output, including debug output.
- The plugin works the same as before the fix.

**Notes**

- Cause found in the code: plugins saved tokens with a plain `open(path, "w")`, so the file got the system's default permissions, usually `644` (readable by everyone). The Spotify plugin also printed the full token in its debug output.
- Confirmed by the implementer (PR #3): the fix covers the Spotify and Beatport plugins. It creates token files as `600`, tightens existing files when they are saved, keeps reading saved tokens, and removes tokens and the Beatport secret from debug output.
- The acceptance tests use Spotify because it logs in automatically with built-in credentials. Beatport needs a user account, so its behaviour is covered by the implementer's automated tests instead.
- Windows does not use these permission bits, so UC-2 is tested on macOS, Linux or WSL only.
