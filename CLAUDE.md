# CLAUDE.md

Source for **ippsec.rocks**, a static search engine over IppSec's YouTube videos. A Python crawler pulls every video's description from the YouTube Data API. Each timestamped line ("chapter") becomes one searchable entry in `dataset.json`. The site searches that file in the browser and links each result to `youtube.com/watch?v=<id>&t=<seconds>`.

Hosted on **GitHub Pages** from `master` (`CNAME` → `ippsec.rocks`). There is no build step and no backend. Pushing to `master` deploys.

## Layout

| Path | Purpose |
|------|---------|
| `yt_crawl.py` | **The crawler.** Regenerates `dataset.json`. |
| `dataset.json` | Generated search index (~550 videos, ~9.5k timestamps, ~780KB, one line). Committed. Don't hand-edit it, and don't `Read` the whole thing; use `python3`/`jq`. |
| `yt.secret`, `htb.secret` | Gitignored. The YouTube Data API key and an HTB App Token, one per file, read by the crawler when `-a`/`--htb-key` aren't given. |
| `.github/workflows/update-dataset.yml` | Weekly GitHub Action (Saturday 16:00 UTC, or the "Run workflow" button) that runs `yt_crawl.py --days 8` and commits `dataset.json`. Needs the `YOUTUBE_API_KEY` and `HTB_API_KEY` repository secrets and fails loudly if either is missing. |
| `index.html`, `logic.js` | The search page. Plain JS, no framework, no bundler. |
| `style.scss` → `style.css` | Styles (`themes/*.scss` are imported). Both files are committed. |
| `contributions/` | A separate "My Contributions" page with its own `contributions.csv` → `dataset.json` (via `csvToDb.py`), `logic.js` and styles. |
| `test-cors.html` | Old copy of the index page. Not linked. |
| `holidayhack2016/` | Static Jekyll output from a 2016 SANS Holiday Hack writeup. Legacy; leave alone. |
| `sponsors/` | Banner images, shown in the commented-out `div.sponsor` block in `index.html`. |

## Updating the dataset

```sh
python3 yt_crawl.py -d 8 -g    # videos published in the last 8 days, merged into the existing dataset
python3 yt_crawl.py -l -g      # just the newest video, merged
python3 yt_crawl.py -g         # full recrawl of every video
git push
```

Keys come from `./yt.secret` (YouTube) and `./htb.secret` (HTB App Token, from the HTB profile settings), or from `-a` and `--htb-key`.

- `-d DAYS` / `--days` fetches the uploads published in the last DAYS days (it looks at the newest page of 50 uploads) and merges them into the dataset at `-o`. `-l [N]` / `--latest` does the same for the newest N uploads (default 1). In both, unknown videos are inserted at the front and known ones are replaced in place, so overlapping windows are harmless. Neither removes videos; a full recrawl does that.
- **Tags are cached.** A video that already has a non-empty tag in the existing dataset keeps it, so only new or untagged videos cost an HTB request. `--retag` ignores the cache and looks every box up again. That is about 450 requests against a 30-per-minute limit, so it takes about 15 minutes.
- Without `htb.secret` the crawler warns and new videos get the playlist tag only (usually none). It exits if HTB rejects the key.
- `-g` commits `dataset.json` with the message `Updated dataset`. Without it, commit by hand. `-o` writes somewhere else (handy for diffing against the current file).
- Never commit a key. `yt.secret` and `htb.secret` are gitignored.
- The GitHub Action runs `--days 8` weekly on `master`. The secrets are written to `yt.secret` and `htb.secret` on the runner. It commits as `github-actions[bot]` and skips the commit when nothing changed.
- The only dependency is `requests`.
- Quota: a full run is one YouTube `playlistItems` call per 50 videos plus the difficulty playlists (about 30 units) and one HTB request per untagged machine video. `--days`/`-l` is two YouTube calls plus one HTB request per new video.

### What the crawler does (`run()` in `yt_crawl.py`)

1. **Tags:** `TagFor` keeps the tag the existing dataset already has for that video id. Otherwise, for a machine video (`HackTheBox - X`, `Hack The Box - X`, `UHC - X`; see `box_title_re`), `BoxName` extracts the box name: first ` - ` segment of the title, `(FIXED)` suffix dropped, non-alphanumerics removed (`Flux Capacitor` → `FluxCapacitor`). `HtbTag` then GETs `machine/profile/<name>` on `labs.hackthebox.com/api/v4` (case-insensitive; a 404 means unknown) and builds `"<os> <difficulty>"` from the response's `os` and `difficultyText`, retrying a trailing `2` as `Two` (`Rope2` → `RopeTwo`). `HtbGet` sleeps on 429 and exits on 401/403. Only when that fails does it fall back to the YouTube playlists: `GetPlaylistTags` reads each playlist in `playlists` (linux/windows × easy/medium/hard/insane) and maps `title → tag` by exact title, fetched lazily on the first title that needs it. A machine video that ends up with no tag prints a warning naming it (currently CriticalOps, which HTB doesn't know, plus the UniCTF talk and Academy intro, which aren't boxes).
2. **Videos:** it reads the channel's "uploads" playlist (from `channel_id`), newest first. With `-d`/`-l` it only takes the items in the window (`PublishedAt` uses `contentDetails.videoPublishedAt`, the moment a scheduled video went public) and merges them into the existing file instead of rebuilding it.
3. **Lines:** `ParseLine` turns each non-empty description line into `[seconds, text]`:
   - `01:23 - Running nmap`, `1:02:03 - ...` and `01:23 Running nmap` all parse (see `timestamp_re`). The separator dash is optional.
   - A line without a leading timestamp becomes `[0, line]`. That's why intro text, links and so on appear as results at the start of a video.

### `dataset.json` format

The file is grouped by video and written as compact JSON (`separators=(',',':')`, UTF-8):

```json
[{"id":"abc123","title":"HackTheBox - Lame","tag":"linux easy","lines":[[0,"Intro text"],[312,"Running nmap"]]}]
```

- `id` is the YouTube video ID.
- `tag` is `"<os> <difficulty>"`, lowercased from HTB's `os` and `difficultyText` (`"linux easy"`, `"openbsd medium"`, `"other insane"`), or the playlist tag when HTB doesn't know the box, or `""` for non-machine videos (tutorials, Sherlocks, VulnHub, HHC2016).
- In `lines`, each `[t, text]` has `t` in seconds, used directly as `&t=` in the link.
- If you change this format, update both `yt_crawl.py` and the loader in `logic.js`.

## Front-end (`logic.js`)

- Loads `./dataset.json` with `fetch` on `DOMContentLoaded`. It flattens the file into `window.dataset`, one entry per line: `{machine, videoId, time, line, haystack}`. `haystack` is `(line + machine + tag).toLowerCase()`, computed once.
- It searches on every `input` event.
- Search builds a regex in which every space-separated word must match: `(?=.*word1)(?=.*word2)`. A word starting with `-` is excluded. It matches against `haystack`. User input is **not** regex-escaped, so characters like `(` or `+` act as regex syntax.
- `replaceStrings` strips the `HackTheBox - `, `VulnHub - ` and `UHC - ` prefixes from titles once, at load time.
- If there are more than `totalLimit` (250) results, it shows an error instead of rendering them.
- Rows are built by string replacement into `searchResultFormat` and inserted with `innerHTML`. Description text is trusted (it's the channel's own text) but not escaped.
- The page state is shown with body classes (`color-no-search`, `color-results-found`, `color-no-results`, `color-too-many-results`), which are styled in `themes/`.

## Local development

```sh
python3 -m http.server 8000   # fetch() needs http://, file:// won't work
```

**SCSS:** edit `style.scss` or `themes/*.scss`, then recompile to `style.css` and commit both. The original setup uses the VS Code Live Sass Compiler (`.vscode/settings.json`: expanded output, no source map). The CLI equivalent:

```sh
sass --no-source-map --style=expanded style.scss style.css
```

**Contributions page:** add a line to `contributions/contributions.csv` (`date;title;link;description`, `;`-separated, newest first). Then regenerate from inside that directory:

```sh
cd contributions && python3 csvToDb.py
```

## Conventions

- Keep it static: no build tooling, no frameworks, no npm. The site must keep working as plain files on GitHub Pages.
- Dataset refresh commits are just `Updated dataset`.
- There are no tests. To check a change, serve the site locally and try a few searches (e.g. `nmap`, `sqli -windows`, `linux hard`). Confirm the result links jump to the right second.
